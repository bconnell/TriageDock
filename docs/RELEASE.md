# Release acceptance

## Source identity

Require the exact release commit to pass all checks in [CI](../.github/workflows/ci.yml). The independent `backend`, `frontend`, `docker`, and `security` jobs must be successful. Do not treat earlier runs or an updated dependency graph as equivalent evidence.

## Product acceptance

- Operator login, incident list, filters, detail panel, acknowledgement and resolution through a real browser.
- Intake rejects requests without an API key; first accepted alert returns 201; repeated identity returns 200 and increments occurrences; resolved incidents reopen.
- Notification records persist, bounded retry failures remain visible, and the receiver may see duplicates.
- Local `.env` remains uncommitted; web port binds to loopback; no database or Redis host ports.
- The README screenshot was captured and visually reviewed from the running application with synthetic demo incidents; browser CI repeats the interaction path on changes.
- External deployment is out of scope; performance at production incident volume and external alert rates is not established.

## GitHub administration

The repository connector can edit source, branches, pull requests and merges, but cannot edit the GitHub repository settings. Release publication uses an explicitly scoped GitHub Actions workflow instead. The owner should finish these settings in GitHub when available:

- An active `main` ruleset requiring pull requests and the `backend`, `frontend`, `docker`, and `security` status checks.
- Prevent forced updates/deletion and remove unnecessary always-allowed administrator bypasses. Avoid imposing approval requirements on a solo-maintainer repository without an available reviewer.
- Repository description and topics reflecting the actual stack; optional image preview once manually checked.
- The one-time release workflow creates `v1.0.0` only when all CI checks on the exact current `main` commit pass. If the release action is blocked by repository token policy, the owner must publish the verified commit manually. Do not retag another commit without an explicit release decision.

## Evidence limitations

CI smoke checks are real containerized HTTP tests. They are not a substitute for an interactive browser review, accessibility audit, performance study, or public deployment security assessment. Do not claim these as passed unless there is independent evidence.

## Hardening candidate acceptance

For any new tag, first execute `scripts/verify-local.ps1` on a suitably resourced development system using pinned dependencies and preserve its output. Perform an isolated Compose walkthrough and real PostgreSQL concurrency/delivery recovery tests. Run the backup-and-restore verification script using an operator-approved test backup. Confirm login abuse, scoped keys, permissions, keyboard-only navigation and reduced-width layout. Review memory consumption and ensure the work is serial.

Merge policy is independent of release policy: source changes may be merged with explicitly documented unverified checks when the owner authorizes this, but **do not publish a new stable release** until all executable gates are green. The existing v1.0.0 tag must remain immutable.
