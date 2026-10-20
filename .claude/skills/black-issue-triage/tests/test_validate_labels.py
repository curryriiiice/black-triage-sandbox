import json

import validate_labels as vl
from triage_common import load_label_policy

POLICY = load_label_policy()
CTX = {
    "repo_labels": POLICY["agent_may_apply"] + POLICY["maintainer_only"],
    "issue": {"existing_labels": ["T: bug"]},
    "duplicate_candidates": [{"number": 5}],
}


def run(labels, outcomes=frozenset(), dup=None, ctx=CTX):
    return vl.validate(labels, ctx, POLICY, set(outcomes), dup)


def test_valid_bug_labels():
    r = run(["C: crash", "F: fmtskip"], outcomes={"crash"})
    assert r["ok"] and r["final_labels"] == ["C: crash", "F: fmtskip"] and not r["warnings"]


def test_maintainer_only_and_unknown_rejected():
    r = run(["R: not a bug", "R: rejected", "stale", "wontfix"])
    assert not r["ok"] and len(r["errors"]) == 4
    assert "maintainer decision" in r["errors"][0]


def test_label_missing_from_repo_rejected():
    ctx = dict(CTX, repo_labels=["C: crash"])
    assert not run(["F: fmtskip"], ctx=ctx)["ok"]


def test_existing_label_dropped():
    r = run(["T: bug", "C: parser"])
    assert r["ok"] and r["final_labels"] == ["C: parser"]


def test_spam_must_be_alone():
    assert not run(["spam / ai", "C: crash"])["ok"]
    assert run(["spam / ai"])["ok"]


def test_duplicate_requires_known_candidate():
    assert not run(["R: duplicate"])["ok"]
    assert not run(["R: duplicate"], dup=99)["ok"]
    assert run(["R: duplicate"], dup=5)["ok"]


def test_single_type_label_and_cap():
    assert not run(["T: style", "T: enhancement"])["ok"]
    r = run(["T: user support"])
    assert r["ok"] and any("two type labels" in w for w in r["warnings"])
    assert not run(["C: crash", "C: parser", "F: comments", "F: strings", "F: linebreak"])["ok"]


def test_repro_backing_warnings():
    r = run(["C: unstable formatting"], outcomes={"reformatted"})
    assert r["ok"] and any("not backed" in w for w in r["warnings"])
    r = run(["S: needs repro"], outcomes={"crash"})
    assert any("contradicts" in w for w in r["warnings"])


def test_main_writes_audit(tmp_path, capsys):
    (tmp_path / "context.json").write_text(json.dumps(CTX))
    (tmp_path / "skill_audit.jsonl").write_text(json.dumps({"event": "repro", "outcome": "crash"})
                                                 + "\n")
    rc = vl.main(["C: crash", "--triage-dir", str(tmp_path)])
    assert rc == 0
    assert "[black-issue-triage v" in capsys.readouterr().out
    events = [json.loads(x)["event"] for x in
              (tmp_path / "skill_audit.jsonl").read_text().splitlines()]
    assert events == ["repro", "validate_labels"]
    assert vl.main(["R: rejected", "--triage-dir", str(tmp_path)]) == 1
