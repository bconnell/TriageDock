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
    )
    for phrase in misleading:
        for text in snippets:
            if phrase in text.lower():
                raise AssertionError(f"Unverified public copy: {phrase!r}")

    assert "30000" in dashboard and "setInterval" in dashboard, "Refresh interval changed; review UI copy"
    assert "30 SECOND REFRESH" in dashboard
    assert "every 30 seconds" in dashboard
    assert "every 30 seconds" in readme
    assert 'request.headers.get("X-TriageDock-Key"' in api
    assert "not a cryptographic payload signature" in contract
    assert "not cryptographically signed" in plan

    for target in ("docs/API.md", "docs/GOAL_AND_LOOP.md"):
        if not (ROOT / target).is_file():
            raise AssertionError(f"Missing linked documentation: {target}")

    print("Public copy consistency checks passed")


if __name__ == "__main__":
    main()
