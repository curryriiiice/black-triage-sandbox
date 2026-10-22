import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_DIR.parent.parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import pytest


@pytest.fixture(autouse=True)
def _not_in_actions(monkeypatch):
    """Unit tests use explicit temp dirs; CI itself runs with GITHUB_ACTIONS=true, which would
    (correctly) make the scripts ignore those overrides. Tests that check the Actions behaviour
    set the variable themselves."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("TRIAGE_CONTEXT_DIR", raising=False)
