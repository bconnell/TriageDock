# Release acceptance

## Source identity

For a release, require independently recorded success on the **exact release candidate**. Run the local source, backend, frontend, security and isolated Docker/browser gates, and record the commit SHA, commands, and results. The [hosted CI configuration](../.github/workflows/ci.yml) provides additional checks when executed; old green runs do not validate newer commits.

## Product acceptance

- Operator login, incident list, filters, detail panel, acknowledgement and resolution through a real browser.
- Intake rejects requests without an API key; first accepted alert returns 201; repeated identity returns 200 and increments occurrences; resolved incidents reopen.
- Notification records persist, bounded retry failures remain visible, and the receiver may see duplicates.
- Local `.env` remains uncommitted; web port binds to loopback; no database or Redis host ports.
- The README screenshot was captured and visually reviewed from the v1.0.0 application with synthetic demo incidents. The manually triggered browser workflow can repeat that path; it has not established results for the newer hardening source.
- External deployment is out of scope; performance at production incident volume and external alert rates is not established.

## GitHub administration

The repository owner should enforce these GitHub protections and publication controls:

- An active `main` ruleset requiring pull requests and the `backend`, `frontend`, `docker`, and `security` status checks.
- Prevent forced updates/deletion and remove unnecessary always-allowed administrator bypasses. Avoid imposing approval requirements on a solo-maintainer repository without an available reviewer.
- Repository description and topics reflecting the actual stack; optional image preview once manually checked.
- Preserve the existing `v1.0.0` tag. Publish a subsequent tag only for an independently validated exact commit, with honest release notes and a recoverable build.

## Evidence limitations

The v1.0.0 smoke and browser checks are historical evidence for that release only. The newer hardening commit needs its own executable evidence. No browser, accessibility, performance, disaster-recovery, or deployment results can be inferred from source inspection.

## Hardening candidate acceptance

For any new tag, first execute `scripts/verify-local.ps1` on a suitably resourced development system using pinned dependencies and preserve its output. Perform an isolated Compose walkthrough and real PostgreSQL concurrency/delivery recovery tests. Run the backup-and-restore verification script using an operator-approved test backup. Confirm login abuse, scoped keys, permissions, keyboard-only navigation and reduced-width layout. Review memory consumption and ensure the work is serial.

Merge policy is independent of release policy: source changes may be merged with explicitly documented unverified checks when the owner authorizes this, but **do not publish a new stable release** until all executable gates are green. The existing v1.0.0 tag must remain immutable.

## Local evidence file

`scripts/verify-local.ps1` verifies a **clean exact commit**. It writes a timestamped PowerShell transcript under the ignored `.validation/` directory in the repository and returns an error on the first failed gate. Save the report identifier and relevant pass/fail lines in the release review. Never publish raw local transcripts without reviewing them for machine paths or other private data. Restore the caller's environment variables and working directory when the gate finishes.

## Isolated database/Redis verification

`scripts/verify-compose.ps1 -ConfirmIsolatedRun` runs the Django suite against a uniquely named, local PostgreSQL/Redis Compose project without publishing network ports. It checks measured memory and disk headroom, uses one build at a time, and keeps an ignored exact-commit transcript. It stops only project-owned containers and **preserves** the isolated volume. This proves database-backed tests only when actually executed; it does not prove browser interactions, live worker delivery, or backup recovery.

## Backup evidence policy

A successful `pg_dump` or `pg_restore --list` verifies only that a dump command produced a readable archive manifest. The backup script first copies to an ignored `.partial` file, then finalizes it and reports a SHA256 digest without overwriting existing backups. A failed copy retains the partial artifact for inspection; no original database volume is altered. Only an isolated `verify-backup.ps1` restoration and data checks support a claim of recoverability. Raw backup files and test transcripts may contain private information and must never be committed or published.
