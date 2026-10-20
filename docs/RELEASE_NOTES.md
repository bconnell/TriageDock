# TriageDock v1.0.0

First public release of a local incident intake and response console using Django, Django REST Framework, PostgreSQL, Celery, Redis, React and TypeScript.

## Included

- API-key-authenticated monitoring intake, stable incident identities, occurrence counting and reopening of resolved incidents.
- Session-authenticated operator UI with search, filters, activity history, acknowledgment and resolution.
- Optional PostgreSQL notification outbox and Celery delivery worker with three attempts and visible delivery results.
- Docker Compose setup, schema migrations, bounded demo data, and documented API.
- Locked dependency versions, Dependabot updates and Python/npm vulnerability checks.
- PostgreSQL-backed tests, frontend checks, actual Docker HTTP smoke verification and headless browser interaction testing.

## Limits

This release is configured for loopback-only local evaluation. It is not an internet-ready alerting or paging service. It does not include tenant isolation, SSO, external rate limiting, guaranteed notification delivery, or production performance benchmarks. See [Security](../SECURITY.md) and [Release acceptance](RELEASE.md).

The repository screenshot was captured from the working interface using synthetic incidents.
