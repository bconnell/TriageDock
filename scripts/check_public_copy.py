"""Check documented behavior against a few executable source facts.

This is a narrow truthfulness regression check, not a subjective writing score.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def main() -> None:
    readme = read("README.md")
    contract = read("docs/API.md")
    plan = read("docs/GOAL_AND_LOOP.md")
    delivery = read("backend/incidents/tasks.py")
    workflow = read(".github/workflows/ci.yml")
    release = read("docs/RELEASE.md")
    ledger = read("docs/EVIDENCE.md")
    security = read("SECURITY.md")
    dashboard = read("frontend/src/App.tsx")
    api = read("backend/incidents/views.py")
    snippets = [readme, contract, plan, dashboard]

    misleading = (
        "stay ahead of every incident",
        "real time visibility",
        "live monitoring",
        "system operational",
        "signed-by-secret-key",
        "built for operational clarity",
        "successfully closed",
        "bounded engineering portfolio project",
        "notification delivery is at-least-once",
    )
    for phrase in misleading:
        for text in snippets:
            if phrase in text.lower():
                raise AssertionError(f"Unverified public copy: {phrase!r}")

    assert "30000" in dashboard and "setInterval" in dashboard, "Refresh interval changed; review UI copy"
    assert "30 SECOND REFRESH" in dashboard
    assert "every 30 seconds" in dashboard
    assert "every 30 seconds" in readme
    assert "a successful delivery is not guaranteed" in readme.lower()
    assert 'request.headers.get("X-TriageDock-Key"' in api
    assert "not a cryptographic payload signature" in contract
    assert "not cryptographically signed" in plan
    assert "MAX_DUE_PER_TICK = 2" in delivery
    assert "at most 2 due rows per run" in readme
    assert "snapshotted when the event is recorded" in contract
    if "workflow_dispatch:" in workflow:
        for name, content in (("README", readme), ("SECURITY", security), ("RELEASE", release)):
            if "CI runs PostgreSQL-backed" in content or "browser CI repeats the interaction path on changes" in content:
                raise AssertionError(f"{name} claims automatic validation, but CI is manual-only")
    assert "current hardening source has not passed those hosted checks" in readme
    assert "have **not** been executed successfully" in ledger
    assert "No stable release or production-readiness claim is authorized" in ledger

    for target in ("docs/API.md", "docs/GOAL_AND_LOOP.md"):
        if not (ROOT / target).is_file():
            raise AssertionError(f"Missing linked documentation: {target}")

    print("Public copy consistency checks passed")


if __name__ == "__main__":
    main()
