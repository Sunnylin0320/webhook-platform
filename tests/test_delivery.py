import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

import httpx
import pytest
import respx

from app import models
from app.worker.delivery import is_retryable_status, send_delivery

URL = "https://customer.example.com/hooks"
SECRET = "test-secret"


def make_webhook():
    return models.Webhook(id=1, user_id="user_1", event_type="invoice.paid",
                          url=URL, secret=SECRET, status="active")


def make_event():
    return models.Event(
        id=uuid.uuid4(),
        user_id="user_1",
        event_type="invoice.paid",
        payload={"invoice_id": "inv_001", "amount": 100},
        created_at=datetime.now(timezone.utc),
    )


@respx.mock
def test_success_sends_signed_request():
    route = respx.post(URL).mock(return_value=httpx.Response(200))
    event = make_event()

    result = send_delivery(make_webhook(), event)

    assert result.ok
    request = route.calls.last.request
    assert request.headers["Webhook-Id"] == str(event.id)
    assert json.loads(request.content)["data"]["amount"] == 100

    timestamp = request.headers["Webhook-Timestamp"]
    signed_content = f"{timestamp}.".encode() + request.content
    expected = hmac.new(SECRET.encode(), signed_content, hashlib.sha256).hexdigest()
    assert request.headers["Webhook-Signature"] == f"v1={expected}"


@respx.mock
def test_server_error_is_retryable():
    respx.post(URL).mock(return_value=httpx.Response(503))

    result = send_delivery(make_webhook(), make_event())

    assert not result.ok
    assert result.retryable
    assert result.error == "HTTP 503"


@respx.mock
def test_client_error_is_not_retryable():
    respx.post(URL).mock(return_value=httpx.Response(400))

    result = send_delivery(make_webhook(), make_event())

    assert not result.ok
    assert not result.retryable


@respx.mock
def test_connection_error_is_retryable():
    respx.post(URL).mock(side_effect=httpx.ConnectError("connection refused"))

    result = send_delivery(make_webhook(), make_event())

    assert not result.ok
    assert result.retryable
    assert "ConnectError" in result.error


@pytest.mark.parametrize(
    "status_code, expected",
    [(500, True), (503, True), (429, True), (408, True), (400, False), (401, False), (404, False)],
)
def test_retryable_status_rules(status_code, expected):
    assert is_retryable_status(status_code) == expected