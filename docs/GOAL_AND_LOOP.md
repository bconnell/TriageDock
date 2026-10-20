# Completion goal and bounded engineering loop

## Goal

Deliver a runnable, documented **TriageDock v1** in a finite scope:
- An operator can authenticate, browse incidents, filter/search, inspect history, acknowledge, and resolve.
- An external monitor can POST an API-key-authenticated alert; repeated `source + external_key` values map to one incident with an incremented occurrence count. Requests are not cryptographically signed.
- Repeated alerts reopen resolved incidents. Every accepted alert and state change has an audit event.
- An optional HTTPS notification receiver can be configured. New and reopened events are recorded in a database outbox and the Celery worker attempts delivery. Delivery may fail.
- PostgreSQL migrations, Redis, Docker Compose, UI, CI, tests and documented failure modes are present.

## Vertical slices

1. **Data and ingestion**: schema → validation → authenticated webhook → dedup/reopen → tests.
2. **Operator response**: session/CSRF → status transition → audit history → UI → tests.
3. **Notification delivery**: persisted outbox → scheduler → bounded retries → delivery evidence.

Each slice must operate across its complete flow before expanding features.

## Horizontal foundations

Use established Django authentication and ORM, DRF serializers, Celery scheduling, React components, environment-driven configuration, and GitHub Actions. Apply shared security, migration, packaging and documentation checks once across all slices.

## Loop (bounded)

Inspect current candidate → identify the **first failing completion gate** → make the smallest safe change → rerun that gate and dependent gates → record evidence → stop when all gates pass. Do not endlessly add low-value checks, speculative features or architecture redesign. If a gate cannot run, state *not verified* rather than pretend success.

## Release gates

| Gate | Evidence |
| --- | --- |
| Backend | Django check, migration drift check, PostgreSQL integration tests |
| Frontend | TypeScript typecheck, UI unit tests, production build |
| Packaging | Production Docker image build and live Compose HTTP smoke |
| Behavior | Alert 201 → same alert 200; status transitions; session access; CSRF |
| Reliability | Outbox success and retry exhaustion tests |
| Security | No committed secrets, authenticated operator API, protected intake key, no exposed database port |
| Documentation | Runnable quick start, accurate API contract, limits, and failure behavior |
| Safety | Writes exclusively inside this repository; no external file/profile/system modifications |

A successful CI proves build, tests and a **containerized smoke flow**. A manually conducted interactive operator walkthrough is still separate evidence and must not be claimed until performed.

## Explicit safety constraints

**Personal files and data safety:** Never delete, modify, rename, move or overwrite user documents, downloads, desktops, profiles, other repositories, credential stores, browser settings, or uncommitted changes. Work only inside TriageDock. Do not stage secret `.env` files.

**System safety:** Do not modify host OS, registry, firewall, system services, startup items, global tooling, or unrelated installations. Docker Compose operates only on this project's services and named volume. Never use global prune/cleanup commands, force pushes, hard resets, or destructive blanket deletes. Branch changes are non-forced and must preserve main until the candidate is validated.
