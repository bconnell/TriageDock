# TriageDock: engineering overview

## What the application does

TriageDock accepts alert reports over an authenticated HTTP endpoint, groups repeated alerts into an incident, and allows signed-in operators to acknowledge or resolve them. Each accepted alert and status change is recorded. A configurable background worker can notify another service.

It is a local-first incident workflow, not a hosted monitoring service or a paging-provider substitute.

## Walkthrough

1. Run the Docker Compose setup and create an operator as described in the [README](../README.md).
2. Send the sample HTTP alert with `X-TriageDock-Key`. The first accepted request returns **201** and a new incident ID.
3. Send the same `source` and `external_key` again. The response is **200**; the incident count increases without creating a second record.
4. Open the incident in the dashboard, review its event history, acknowledge it, then resolve it.
5. Send the alert again. The existing resolved incident reopens and the history records that transition.
6. Optionally configure an HTTPS notification receiver to inspect the outbox status and retry behavior. Leave it unset if you do not control a receiver.

## Why these components

| Component | Responsibility |
| --- | --- |
| Django + Django REST Framework | Session authentication, CSRF protection, JSON validation, incident API, ORM and migrations |
| PostgreSQL | Canonical incident, event and notification records; transaction-backed updates and unique incident identity |
| Redis + Celery | Job transport and periodic delivery attempts for pending notifications |
| React + TypeScript | Operator console for incident search, filtering, history and transitions |
| Docker Compose | Isolated local app, database, queue, worker and scheduler |
| GitHub Actions | PostgreSQL tests, dependency audits, TypeScript build, Docker runtime and browser interaction proof |

## Explicit tradeoffs

- Browser information refreshes every 30 seconds, rather than using push or WebSockets.
- Authenticated readers and permission-granted operators have separate responsibilities. This is not a multi-tenant product.
- Incoming API keys authenticate the sender but do not sign the request body. Public exposure requires TLS and independent rate limits.
- Notifications are best effort. They can be lost after retry exhaustion or delivered more than once. Consumers must deduplicate the `event_id`.
- Local Compose does not establish external operational reliability, disaster recovery, or large-volume performance.

## Verified evidence

The [CI configuration](../.github/workflows/ci.yml) specifies PostgreSQL-backed Django tests, frontend typechecking and unit tests, Python/npm dependency audits, a container build and a live HTTP smoke test. Its Selenium script is intended to sign in with a synthetic operator and exercise acknowledge/resolve interactions. These checks have not been rerun on the newer hardening candidate.

The screenshot shows the real CI interface with four synthetic alert records; it is not a design mockup. Independent human testing and deployment hardening are separate acceptance tasks.

## Additional default-branch hardening (not yet tagged)

- Read-only history in Django Admin and operator-only status changes.
- Redis-backed sign-in and intake limits, strong secret validation, scoped API keys with revocation.
- Recoverable Celery outbox claims with event-time payloads and rejected redirects.
- Event pagination, monotonic severity for active incidents, database/queue/worker readiness, memory budgets, and keyboard focus management.
- Local source/test gates and isolated backup/restore scripts.

The previous v1.0.0 CI evidence does **not** prove this newer candidate. Follow the local gate and release contract before claiming test success or promoting it to production.
