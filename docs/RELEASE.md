# Release acceptance

## Source identity

Require the exact release commit to pass all checks in [CI](../.github/workflows/ci.yml). The independent `backend`, `frontend`, `docker`, and `security` jobs must be successful. Do not treat earlier runs or an updated dependency graph as equivalent evidence.

## Product acceptance

- Operator login, incident list, filters, detail panel, acknowledgement and resolution through a real browser.
- Intake rejects requests without an API key; first accepted alert returns 201; repeated identity returns 200 and increments occurrences; resolved incidents reopen.
- Notification records persist, bounded retry failures remain visible, and the receiver may see duplicates.
- Local `.env` remains uncommitted; web port binds to loopback; no database or Redis host ports.
- Screenshot shown in the README, when present, must be captured from the actual application in its demo-data mode and reviewed for legibility.
- External deployment is out of scope; performance at production incident volume and external alert rates is not established.

## GitHub administration

The current connection can change repository source, branches, pull requests, and merges, but does not expose repository settings edits or GitHub release publishing. The owner should finish these controls in GitHub settings when available:

- An active `main` ruleset requiring pull requests and the `backend`, `frontend`, `docker`, and `security` status checks.
- Prevent forced updates/deletion and remove unnecessary always-allowed administrator bypasses. Avoid imposing approval requirements on a solo-maintainer repository without an available reviewer.
- Repository description and topics reflecting the actual stack; optional image preview once manually checked.
- Create a `v1.0.0` tag and release only for the final reviewed commit and use factual release notes.

## Evidence limitations

CI smoke checks are real containerized HTTP tests. They are not a substitute for an interactive browser review, accessibility audit, performance study, or public deployment security assessment. Do not claim these as passed unless there is independent evidence.
