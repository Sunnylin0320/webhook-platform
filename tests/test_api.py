def register(client, user_id="user_1", event_type="invoice.paid", url="https://example.com/hook"):
    response = client.post(
        "/v1/webhook", json={"user_id": user_id, "event_type": event_type, "url": url}
    )
    assert response.status_code == 201
    return response.json()


def test_register_returns_secret_only_once(client):
    created = register(client)
    assert created["status"] == "active"
    assert len(created["secret"]) == 64

    fetched = client.get(f"/v1/webhook/{created['id']}").json()
    assert "secret" not in fetched


def test_register_rejects_invalid_url(client):
    response = client.post(
        "/v1/webhook", json={"user_id": "user_1", "event_type": "invoice.paid", "url": "not-a-url"}
    )
    assert response.status_code == 422


def test_deactivate_keeps_other_fields(client):
    created = register(client)

    response = client.put(f"/v1/webhook/{created['id']}", json={"status": "inactive"})

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    assert response.json()["url"] == created["url"]


def test_delete_endpoint(client):
    created = register(client)

    assert client.delete(f"/v1/webhook/{created['id']}").status_code == 204
    assert client.get(f"/v1/webhook/{created['id']}").status_code == 404


def test_publish_fans_out_to_matching_active_endpoints(client, enqueued):
    register(client, url="https://example.com/a")
    register(client, url="https://example.com/b")
    inactive = register(client, url="https://example.com/c")
    register(client, user_id="user_2", url="https://example.com/d")
    client.put(f"/v1/webhook/{inactive['id']}", json={"status": "inactive"})

    response = client.post(
        "/v1/events",
        json={"user_id": "user_1", "event_type": "invoice.paid", "payload": {"amount": 100}},
    )

    assert response.status_code == 202
    assert response.json()["deliveries_created"] == 2
    assert len(enqueued) == 2


def test_publish_without_subscribers_creates_nothing(client, enqueued):
    response = client.post(
        "/v1/events",
        json={"user_id": "user_1", "event_type": "issue.opened", "payload": {}},
    )

    assert response.status_code == 202
    assert response.json()["deliveries_created"] == 0
    assert enqueued == []