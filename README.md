# TriageDock

**Incident intake, triage and notification workflow.**

TriageDock is a small operational console built with **Python 3.13, Django 6.1, Django REST Framework, PostgreSQL, Redis, Celery, React 19 and TypeScript**. It is a bounded engineering portfolio project, not a claim of production-scale incident paging.

Operator features: secure session login, current incident feed, status and severity filters, search, detail history, acknowledgement, resolution, counts, live polling, and notification delivery status. Monitoring tools send alerts to a protected API; repeated alerts are deduplicated and resolved alerts reopen.

## Quick start (Docker Compose)

Requires Docker Engine + Compose plugin.

1. Copy `.env.example` to `.env`; replace **all three** sample secrets (`DJANGO_SECRET_KEY`, `INGEST_API_KEY`, `POSTGRES_PASSWORD`). Do not commit `.env`.
2. Run `docker compose up --build -d`.
3. Run `docker compose exec web python manage.py createsuperuser` and create an operator.
4. Visit **http://localhost:8000** and sign in.
5. Optional safe sample content: `docker compose exec web python manage.py seed_demo`.

The app listens on **127.0.0.1:8000**, not a public interface. The DB and Redis have no published ports. Stop with `docker compose down` (the database named volume is preserved). **Do not use `docker compose down -v`** unless intentionally removing this project's data.

### Send a real alert

Using a shell with `INGEST_API_KEY` set to the same value as your private `.env`:

```bash
curl -X POST http://localhost:8000/api/v1/alerts/ \
  -H "Content-Type: application/json" \
  -H "X-TriageDock-Key: $INGEST_API_KEY" \
  --data '{"source":"checkout-api","external_key":"http-5xx","title":"Elevated error rate","description":"5xx errors above threshold","severity":"critical"}'
```

Post the same JSON again to observe an increased occurrence count. Resolve it in the dashboard and post again to observe reopening. On Windows PowerShell, use `curl.exe` and set the key in `$env:INGEST_API_KEY`; substitute `$env:INGEST_API_KEY` in the command.

### Optional HTTPS notification delivery

Set `NOTIFICATION_WEBHOOK_URL` to an HTTPS receiver you control and restart the Compose services. Each **new or reopened** alert creates a durable outbox entry. Celery beat scans pending work every 15 seconds, and workers attempt a bounded HTTPS POST with a 5 second timeout, 30/60 second backoff, and a three-attempt limit. Failed deliveries stay visible and are not silently reported as successful. Leave the URL empty to disable outbound notifications.

## Local developer workflow

- Backend: Python 3.13, `pip install -r backend/requirements-dev.txt`. Set `DJANGO_DEBUG=1 DATABASE_ENGINE=sqlite` for local unit development, then from `backend/` run `python manage.py migrate`, `python manage.py createsuperuser`, and `python manage.py runserver 127.0.0.1:8000`. SQLite is a development convenience, **not** proof of PostgreSQL concurrency behavior.
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

## Docs

- [API reference](docs/API.md)
- [Completion goal, vertical slices, horizontal foundations and release gates](docs/GOAL_AND_LOOP.md)

## Scope and limitations

- The default deployment is **local-only**. A public deployment needs managed TLS termination, secure cookies (`SECURE_COOKIES=1`), suitable `ALLOWED_HOSTS` and trusted origins, network edge rate limiting, secret management, monitoring, backups, and restore exercises.
- Operator permissions are a single authenticated role; there is no tenant isolation, SSO, escalation policy, SMS, or email paging.
- Notification delivery is at-least-once, not exactly-once. The dispatcher is intentionally bounded to 50 due rows per run. It is not a high-throughput enterprise notification service.
- The frontend polls every 30 seconds; no WebSocket or instant push is claimed.
- A small liveness endpoint does not prove database or queue readiness.
- No credentials, customer data, or real alert endpoints should be committed to this repository.

**License:** MIT. Copyright © 2026 Brandon Connell.
