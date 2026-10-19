open -a Docker                      # 1. Open Docker Desktop, wait until the whale icon stops animating
docker start webhook-db             # 2. Start the database
docker start webhook-redis          # Start Redis (the task queue)
celery -A app.worker.celery_app:celery_app worker --loglevel=info   # Celery worker (sends webhooks)
docker ps                           # 3. Check webhook-db is Up
source .venv/bin/activate           # 4. Activate the virtual env, (.venv) should appear

uvicorn app.main:app --reload               # Webhook platform → http://127.0.0.1:8000/docs
uvicorn tools.receiver:app --port 9000 --reload   # Fake customer endpoint → http://127.0.0.1:9000

# Open psql (\dt list tables, \d <table> show schema, \q quit)
docker exec -it webhook-db psql -U webhook

# Run a single query
docker exec -it webhook-db psql -U webhook -c "\dt"
docker exec -it webhook-db psql -U webhook -c "SELECT id, user_id, event_type, url, status FROM webhooks;"
docker exec -it webhook-db psql -U webhook -c "SELECT id, user_id, event_type, created_at FROM events;"
docker exec -it webhook-db psql -U webhook -c "SELECT id, event_id, webhook_id, status, attempts, last_error FROM deliveries ORDER BY id;"

docker ps -a                        # List all containers, including stopped ones
docker logs webhook-db              # Show database logs, useful for debugging
docker stop webhook-db              # Stop the database (data is kept)

docker run --name webhook-db \
  -e POSTGRES_USER=webhook \
  -e POSTGRES_PASSWORD=webhook \
  -e POSTGRES_DB=webhook \
  -p 5432:5432 \
  -v webhook-data:/var/lib/postgresql/data \
  -d postgres:16

pip freeze > requirements.txt       # Only needed after installing new packages
git status                          # Check what will be committed