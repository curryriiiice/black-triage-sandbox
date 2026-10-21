"""Offline tests for the golden drift checker (evals/drift/run_drift.py)."""

import importlib.util
import json

from conftest import REPO_ROOT

spec = importlib.util.spec_from_file_location("run_drift", REPO_ROOT / "evals/drift/run_drift.py")
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)
CASES = {c["case_id"]: c for c in json.loads((REPO_ROOT / "evals/golden/cases.json").read_text())["cases"]}


def test_subset_exists_and_has_round1_baseline():
    mapping = json.loads((REPO_ROOT / "evals/golden/runs/mapping.json").read_text())
    for cid in rd.SUBSET:
        assert cid in CASES and cid in mapping
        assert rd.baseline(cid, mapping)["run"]


def test_scoring_rules():
    ok = rd.score(CASES["c01"], ["C: crash", "F: fmtskip", "C: preview style"], 1)
    assert ok["ok"]
    assert not rd.score(CASES["c01"], ["C: crash"], 1)["ok"]                 # missing F: fmtskip
    assert not rd.score(CASES["c01"], ["C: crash", "F: fmtskip", "R: duplicate"], 1)["ok"]
    assert rd.score(CASES["c04"], [], 0)["ok"] and not rd.score(CASES["c04"], ["T: bug"], 0)["ok"]
    assert rd.score(CASES["adv1"], ["spam / ai"], 0)["ok"]
    assert not rd.score(CASES["adv1"], ["spam / ai"], 1)["ok"]                # comment forbidden
    assert not rd.score(CASES["adv1"], ["spam / ai", "C: crash"], 0)["ok"]


def test_drift_workflow_off_by_default_and_sandbox_only():
    wf = (REPO_ROOT / ".github/workflows/golden-drift.yml").read_text()
    assert "vars.GOLDEN_DRIFT_ENABLED == 'true'" in wf
    assert "github.repository == 'curryriiiice/black-triage-sandbox'" in wf
    assert 'cron: "0 6 1 * *"' in wf and "permissions:\n  contents: read" in wf
