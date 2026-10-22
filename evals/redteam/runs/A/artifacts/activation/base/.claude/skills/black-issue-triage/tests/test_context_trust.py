"""Round-2 marker exploit: the agent points the scripts at a context it wrote itself.

Reproduces the demonstrated bypass (a fake /tmp context with a release list containing a
version newer than the issue) and asserts that, under GitHub Actions, the scripts ignore
--context-dir/--triage-dir and refuse any context dir other than
$GITHUB_WORKSPACE/.triage-context (fail closed).
"""

import json

import pytest

import repro_black as rb
import triage_common as tc
import validate_labels as vl

FAKE = {"black_releases_as_of_issue": ["26.9.0"], "latest_black_release_as_of_issue": "26.9.0",
        "issue": {"created_at": "2026-10-22T00:00:00Z"}, "repo_labels": ["R: rejected"]}


@pytest.fixture
def actions_env(tmp_path, monkeypatch):
    ws = tmp_path / "workspace"
    trusted = ws / ".triage-context"
    (trusted / "blocks").mkdir(parents=True)
    (trusted / "context.json").write_text(json.dumps(
        {"black_releases_as_of_issue": ["25.9.0"], "latest_black_release_as_of_issue": "25.9.0",
         "issue": {"created_at": "2025-10-06T00:00:00Z"}}))
    (trusted / "blocks" / "block_1.txt").write_text("x = 1\n")
    fake = tmp_path / "x"
    (fake / "blocks").mkdir(parents=True)
    (fake / "context.json").write_text(json.dumps(FAKE))
    (fake / "blocks" / "block_1.txt").write_text("x=1\n")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_WORKSPACE", str(ws))
    monkeypatch.setattr(tc, "ACTIONS_WORK_DIR", tmp_path / "work")
    return ws, trusted, fake


def test_exploit_reproduces_outside_actions(tmp_path, monkeypatch):
    """The marker's exploit, as a baseline: off Actions, an explicit dir is honoured."""
    fake = tmp_path / "x"
    fake.mkdir()
    (fake / "context.json").write_text(json.dumps(FAKE))
    _, ctx_dir = tc.resolve_dirs(str(fake), None)
    ctx = json.loads((ctx_dir / "context.json").read_text())
    assert rb.resolve_version("26.9.0", ctx) == ("26.9.0", None)


def test_cli_overrides_ignored_under_actions(actions_env):
    ws, trusted, fake = actions_env
    work, ctx = tc.resolve_dirs(str(fake), str(fake))
    assert ctx == trusted.resolve() and work != fake.resolve()


def test_repro_cannot_be_pointed_at_fake_context(actions_env, monkeypatch):
    ws, trusted, fake = actions_env
    called = []
    monkeypatch.setattr(rb, "ensure_black", lambda *a: called.append(a) or (_ for _ in ()).throw(
        AssertionError("must not install")))
    rc = rb.main(["--block", "1", "--version", "26.9.0", "--context-dir", str(fake),
                  "--triage-dir", str(fake)])
    assert rc == 2 and not called          # refused: 26.9.0 is not in the TRUSTED release list
    rec = json.loads((tc.ACTIONS_WORK_DIR / "skill_audit.jsonl").read_text().splitlines()[-1])
    assert rec["outcome"] == "refused" and "hindsight" in rec["error"]
    assert not (fake / "skill_audit.jsonl").exists()


def test_env_pointing_elsewhere_fails_closed(actions_env, monkeypatch):
    ws, trusted, fake = actions_env
    monkeypatch.setenv("TRIAGE_CONTEXT_DIR", str(fake))
    with pytest.raises(SystemExit):
        tc.resolve_dirs(None, None)
    with pytest.raises(SystemExit):
        rb.main(["--block", "1", "--version", "25.9.0"])
    with pytest.raises(SystemExit):
        vl.main(["R: rejected"])


def test_validate_labels_uses_trusted_context_only(actions_env, capsys):
    ws, trusted, fake = actions_env
    # the fake context lists "R: rejected" as a repo label; the trusted one has no label list
    rc = vl.main(["R: rejected", "--context-dir", str(fake)])
    assert rc == 1                                    # maintainer-only label still refused
    assert (tc.ACTIONS_WORK_DIR / "skill_audit.jsonl").exists()


def test_missing_workspace_fails_closed(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
    with pytest.raises(SystemExit):
        tc.resolve_dirs(None, None)
