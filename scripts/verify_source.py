"""Dependency-free source gate: parses Python and checks release contracts.

It is not a substitute for Django, TypeScript, browser, or PostgreSQL tests.
"""
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def main():
    sources = sorted((ROOT / "backend").rglob("*.py")) + sorted((ROOT / "scripts").glob("*.py"))
    for path in sources:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    settings = (ROOT / "backend/config/settings.py").read_text(encoding="utf-8")
    views = (ROOT / "backend/incidents/views.py").read_text(encoding="utf-8")
    tasks = (ROOT / "backend/incidents/tasks.py").read_text(encoding="utf-8")
    admin = (ROOT / "backend/incidents/admin.py").read_text(encoding="utf-8")
    client = (ROOT / "frontend/src/App.tsx").read_text(encoding="utf-8")
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    require("IsIncidentOperator" in views and "has_perm" in (ROOT / "backend/incidents/permissions.py").read_text(),
            "Incident state-change authorization missing")
    require("IngestRateThrottle" in views and "_too_many_logins" in views,
            "Intake or login throttling missing")
    require("has_delete_permission" in admin and "has_change_permission" in admin,
            "Read-only incident admin missing")
    require("claim_token" in tasks and "with transaction.atomic()" in tasks and "build_opener" in tasks,
            "Notification claim/recovery contract missing")
    require('REDIS_CACHE_URL' in compose and "DATA_UPLOAD_MAX_MEMORY_SIZE" in settings,
            "Cache or size protection missing")
    require("aria-modal" in client and "requestVersion" in client,
            "Frontend interaction safety changed")
    require((ROOT / "backend/incidents/migrations/0002_delivery_claims.py").is_file(),
            "Migration for durable outbox claims missing")
    require((ROOT / "backend/requirements.lock").is_file() and
            (ROOT / "frontend/package-lock.json").is_file(),
            "Reviewed dependency locks missing")
    for path in (ROOT / "backend").rglob("*.py"):
        require("TODO: pretend test passed" not in path.read_text(encoding="utf-8"),
                "Unverified proof placeholder")
    print("Parsed", len(sources), "Python files; source-contract assertions passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Source gate FAILED:", error, file=sys.stderr)
        sys.exit(1)
