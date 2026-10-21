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
| Security | No committed secrets, authenticated operator API, protected intake key, no exposed database port, dependency vulnerability audit |
| Documentation | Runnable quick start, accurate API contract, limits, and failure behavior |
| Safety | Writes exclusively inside this repository; no external file/profile/system modifications |

A successful run of the full CI workflow establishes its specific automated tests for the checked commit, not for later commits. The checked-in browser script covers login, incident listing, detail, acknowledgement and resolution in Compose with synthetic data. It must be executed on the target candidate before making a completion claim. Human testing remains separate.

## Explicit safety constraints

**Personal files and data safety:** Never delete, modify, rename, move or overwrite user documents, downloads, desktops, profiles, other repositories, credential stores, browser settings, or uncommitted changes. Work only inside TriageDock. Do not stage secret `.env` files.

**System safety:** Do not modify host OS, registry, firewall, system services, startup items, global tooling, or unrelated installations. Docker Compose operates only on this project's services and named volume. Never use global prune/cleanup commands, force pushes, hard resets, or destructive blanket deletes. Branch changes are non-forced and must preserve main until the candidate is validated.

## Hardening completion gates (current default branch)

- **Vertical authorization:** Reader versus operator, Django Admin read-only history, login and ingest limits, scoped keys and revocation; prove denial and permission paths.
- **Vertical delivery:** Immutable payload snapshot, crash-expiring claims, HTTP outside transactions, bounded attempts, redirect rejection and worker heartbeat; prove timeout/reclaim/duplicate semantics.
- **Vertical recovery:** Isolated database dump and restore with explicit file safety; preserve original volumes and test data.
- **Horizontal verification:** Python parsing, Django migration drift, backend regression tests, frontend typecheck/tests/build, Compose configuration, keyboard and responsive inspection, resource ceilings, truthful documentation, pinned dependencies.
- **Exit criteria:** Every executed local gate records actual evidence for the exact commit. Do not infer a pass for an unavailable runner. Unexecuted tests are marked **not verified** and cannot be described as passed.

**Personal file/data safety:** Only modify TriageDock source paths and explicitly designated `backups/` outputs; preserve other files, uncommitted changes and history. No deletion or overwrite of user-created data or backup artifacts.

**System safety:** No OS, registry, security product, startup, services, firewall, browser profile or global development-tool changes. Validate free RAM and disk before heavy tasks. Use one build/test engine at a time, bounded Docker limits and controlled shutdown of project-owned services. Stop on resource uncertainty.
