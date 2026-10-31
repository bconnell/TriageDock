# Verification evidence

## Published release (historical)

The published [v1.0.0 release](https://github.com/bconnell/TriageDock/releases/tag/v1.0.0)
targets commit `fa44265034b4b1113f4dde1e75d7d727e7e2f15d`.
GitHub reports completed `backend`, `frontend`, `docker`, and `security`
checks with successful conclusions for that exact commit on 20 October 2026.
Those results are **not evidence for any newer commit**.

## Current source after v1.0.0

The post-release source contains implementations and regression test cases for:

- Reader/operator authorization and login abuse limits, including legitimate
  repeated login and shared-address failure accounting.
- Source-scoped ingest credentials, bounded history, and PostgreSQL
  simultaneous-ingest probes.
- Outbox claim recovery, a two-delivery dispatch budget, event-time payload
  snapshots, optional HMAC-signed webhooks, refusal to follow redirects,
  and simultaneous delivery-claim probes.
- Accessible incident details, race-safe detail selection, session expiry
  handling, and a keyboard-accessible sign-out control down to a 320px viewport.
- Guarded 64 KiB alert bodies, real-session CSRF negative tests, backup
  staging and checksum comparison, isolated restore startup, and resource
  preflight scripts.

**Execution status for post-release source:** Backend tests, migration checks,
frontend type checking/build/tests, browser acceptance, PostgreSQL concurrency,
local dependency audits, live webhook receiver, and backup/restore exercises
have **not** been executed successfully against the post-release code in this
session. No stable release or production-readiness claim is authorized.

An isolated Python 3.13 check of `urllib.request.Request` HMAC header handling
succeeded in this session. It tested Python's header behavior alone, **not** the
Django integration, actual delivery worker, or production deployment.

## Required exact-commit acceptance

Run and record the exact source revision, test environment, exit code, and
relevant results for each gate before writing public completion claims:

1. Review the complete Git diff and `python scripts/check_public_copy.py`.
2. Run `scripts/verify-local.ps1` with repository-local dependencies.
3. Run `scripts/verify-compose.ps1 -ConfirmIsolatedRun` against an isolated
   PostgreSQL/Redis test project when resource gates permit.
4. Exercise the actual UI at desktop, tablet, and mobile widths with keyboard
   navigation, authorization checks, and incident transitions.
5. Test outbound delivery, signature verification, retries, replay rejection,
   worker restarts, and the failure/duplicate cases with an isolated receiver.
6. Create an authorized local database backup and verify restoration into a
   new isolated database. Inspect record counts; do not touch the live volume.
7. Run a fresh dependency, secret, legal/privacy/IP applicability and
   documentation claim review for the exact candidate.
8. Publish a later release only after each relevant executable gate has
   recorded evidence and the reviewed commit matches the tag.

**Safety:** No test may overwrite personal files, unrelated repositories,
real alerts, existing database volumes or user backups. Stop when RAM,
commit or disk budgets cannot be measured or are insufficient. Tests must not
modify OS settings or bypass security controls. All destructive cleanup
requires specific authorization.

A failed or unavailable check remains marked **not verified**. Merging a source
change cannot substitute for a test result.
