# TriageDock

**Receive monitoring alerts, track incidents, and record operator actions.**

TriageDock accepts alerts from monitoring tools and groups repeated reports under the same incident. Operators can review the incident history, acknowledge incidents, and mark them resolved in a browser. An optional worker sends notifications to a configured HTTPS webhook.

The stack is **Python 3.13, Django 6.1, Django REST Framework, PostgreSQL, Redis, Celery, React 19, and TypeScript**.

The browser uses Django session authentication. The incident list supports search and filters by status and severity, with updates requested every 30 seconds while the page is open. An alert with the same `source` and `external_key` increments the existing incident's occurrence count. A new report for a resolved incident reopens it.

## Quick start (Docker Compose)

Requires Docker Engine + Compose plugin.

1. Copy `.env.example` to `.env`; replace **all three** sample secrets (`DJANGO_SECRET_KEY`, `INGEST_API_KEY`, `POSTGRES_PASSWORD`). Do not commit `.env`.
2. Run `docker compose up --build -d`.
3. Run `docker compose exec web python manage.py createsuperuser` and create an operator.
4. Visit **http://localhost:8000** and sign in.
5. Optional safe sample content: `docker compose exec web python manage.py seed_demo`.

The app listens on **127.0.0.1:8000**, not a public interface. The DB and Redis have no published ports. Stop with `docker compose down` (the database named volume is preserved). **Do not use `docker compose down -v`** unless intentionally removing this project's data.

### Send a test alert

Using a shell with `INGEST_API_KEY` set to the same value as your private `.env`:

```bash
curl -X POST http://localhost:8000/api/v1/alerts/ \
  -H "Content-Type: application/json" \
  -H "X-TriageDock-Key: $INGEST_API_KEY" \
  --data '{"source":"checkout-api","external_key":"http-5xx","title":"Elevated error rate","description":"5xx errors above threshold","severity":"critical"}'
```

Send the same alert again to increment the occurrence count. Mark the incident resolved in the dashboard, then send it again to see it reopen. The key authenticates the sending client; it is **not** a cryptographic signature of the alert body.

On Windows PowerShell, set `$env:INGEST_API_KEY` to the same value stored in your local `.env` file. Use `curl.exe` rather than the PowerShell `curl` alias and replace `$INGEST_API_KEY` in the example above with `$env:INGEST_API_KEY`.

### Optional HTTPS notification delivery

Set `NOTIFICATION_WEBHOOK_URL` to an HTTPS endpoint you control and restart the Compose services. A newly created or reopened incident adds a notification record to PostgreSQL. Celery beat checks for pending deliveries every 15 seconds. The worker attempts an HTTP POST with a five second timeout and retries after 30 and 60 seconds, up to three attempts. The incident detail view shows delivery attempts and failures. Leave the URL empty to disable notifications. Delivery is not guaranteed; receivers must deduplicate repeated requests using `event_id`.

## Local developer workflow

- Backend: use Python 3.13 and install `backend/requirements-dev.txt`. In your shell, set `DJANGO_DEBUG=1` and `DATABASE_ENGINE=sqlite` (on Windows PowerShell use `$env:DJANGO_DEBUG = '1'` and `$env:DATABASE_ENGINE = 'sqlite'`). From `backend/`, run `python manage.py migrate`, `python manage.py createsuperuser`, then `python manage.py runserver 127.0.0.1:8000`. SQLite is suitable for local development, but does not verify PostgreSQL concurrency behavior.
- Frontend: from `frontend/`, run `npm install` and `npm run dev`. Vite proxies `/api` to the Django server. Open **http://127.0.0.1:5173**.
- Backend checks: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test incidents`.
- Frontend checks: `npm run typecheck`, `npm test`, `npm run build`.
- CI uses actual PostgreSQL for backend integration tests, builds the Docker image, and boots the real Docker Compose stack for an HTTP smoke test.

## Architecture

```text
External monitor -- X-TriageDock-Key --> Django REST intake
                                         | transaction
                                         v
                                   PostgreSQL
                                    |       |
                              incidents   delivery outbox
                                    |       |
                      React UI <-- DRF     Celery beat -> Redis -> worker -> HTTPS webhook
                             session/CSRF
```

Authentication and CSRF are provided by Django. No public account registration exists; operators are created intentionally through Django's management command. Notification receivers must deduplicate `event_id`. External HTTP delivery cannot offer exactly-once semantics.

## Documentation

- [API endpoints and authentication](docs/API.md)
- [Development scope and verification](docs/GOAL_AND_LOOP.md)

Framework references: [Django authentication](https://docs.djangoproject.com/en/stable/topics/auth/default/), [Django REST Framework authentication](https://www.django-rest-framework.org/api-guide/authentication/), [Celery tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html), and [Docker Compose](https://docs.docker.com/compose/).

## Scope and limitations

- The default deployment is **local-only**. A public deployment needs managed TLS termination, secure cookies (`SECURE_COOKIES=1`), suitable `ALLOWED_HOSTS` and trusted origins, network edge rate limiting, secret management, monitoring, backups, and restore exercises.
- Every authenticated Django user can access the operator API. There are no operator roles, per-incident permissions, tenant separation, SSO, escalation policies, SMS, or email paging.
- Notification delivery is best effort, with up to three attempts per event. An event can be delivered more than once, and a successful delivery is not guaranteed. The dispatcher processes at most 50 due rows per run; it is not designed for high-volume paging.
- The frontend polls every 30 seconds; no WebSocket or instant push is claimed.
- A small liveness endpoint does not prove database or queue readiness.
- No credentials, customer data, or real alert endpoints should be committed to this repository.

**License:** MIT. Copyright © 2026 Brandon Connell.
