# Contributing

TriageDock is a small incident-management application. Contributions should preserve its documented local-first scope unless a change is explicitly proposed and reviewed.

1. Open an issue describing a defect or a bounded improvement.
2. Work on a branch; do not push straight to `main`.
3. Keep changes narrow. Update tests when modifying API behavior, persistence, authentication, or failure recovery.
4. Use the commands in the [README](README.md) to run Django tests, frontend checks, and the Docker Compose smoke flow.
5. Keep documentation and interface text accurate. Do not claim real-time updates, successful delivery, or service health without direct evidence.
6. Do not include secrets, production alerts, personally identifiable information, proprietary assets, or unlicensed third-party material.

**Dependency updates:** run `npm install --package-lock-only` inside `frontend/` when its package inputs change. To regenerate Python locks using uv 0.13.4, from the repository root run:

```sh
uv pip compile --python-version 3.13 --output-file backend/requirements.lock backend/requirements.txt
uv pip compile --python-version 3.13 --output-file backend/requirements-dev.lock backend/requirements-dev.txt
```

Check the resolved versions and CI before merging. Lockfiles are source-controlled; never bypass failing checks by relaxing or suppressing them. A successful build is not proof that an interactive screen is visually correct.

**Safety:** Only modify files in this repository. Preserve untracked and uncommitted work. Never run blanket cleanup, destructive git commands, global tooling updates, or system/profile changes as a convenience. The local database volume contains user-created incidents: `docker compose down` preserves it, while `-v` deletes it and must not be used without explicit data-removal intent.

## Local release proof

Use `scripts/verify-local.ps1` with repository-local dependencies. Record exact commit SHA, Python/Django migrations, test results and frontend verification outputs. Do not silently skip failed or unavailable checks. Manual browser review, database restore verification and Docker runtime are separate gates; never infer them from `ast.parse` or a source grep. Treat all directories outside this repository as read-only. Keep builds sequential on resource-constrained hardware.
