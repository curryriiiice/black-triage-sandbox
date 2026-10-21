"""Drift checks between the skill, the workflow source, and the compiled lock file.

Hard restrictions live in the workflow (safe-outputs); the skill's policy file mirrors them
so the agent can self-check. These tests fail if the two disagree, or if the compiled
.lock.yml is stale relative to the label policy.
"""

import json
import re

from conftest import REPO_ROOT, SKILL_DIR
from triage_common import load_label_policy

WF_MD = REPO_ROOT / ".github" / "workflows" / "issue-triage.md"
WF_LOCK = REPO_ROOT / ".github" / "workflows" / "issue-triage.lock.yml"
POLICY = load_label_policy()


def _yaml_list(text: str, parent: str, key: str) -> list[str]:
    """Tiny extractor for `parent:` -> `key:` -> `- "item"` lists (no PyYAML needed)."""
    block = re.search(rf"^  {re.escape(parent)}:\n(.*?)(?=^  \S)", text, re.S | re.M).group(1)
    items = re.search(rf"^    {re.escape(key)}:\n((?:      - .*\n)+)", block, re.M).group(1)
    return [re.sub(r'^\s*- "?(.*?)"?\s*$', r"\1", ln) for ln in items.splitlines()]


def test_workflow_allowlist_matches_policy():
    md = WF_MD.read_text()
    assert _yaml_list(md, "add-labels", "allowed") == POLICY["agent_may_apply"]
    assert _yaml_list(md, "add-labels", "blocked") == POLICY["maintainer_only"]
    assert not set(POLICY["agent_may_apply"]) & set(POLICY["maintainer_only"])


def test_lock_file_compiled_from_current_policy():
    lock = WF_LOCK.read_text()
    m = re.search(r'GH_AW_SAFE_OUTPUTS_HANDLER_CONFIG: "(.*)"', lock)
    cfg = json.loads(m.group(1).encode().decode("unicode_escape"))
    assert cfg["add_labels"]["allowed"] == POLICY["agent_may_apply"]
    assert cfg["add_labels"]["blocked"] == POLICY["maintainer_only"]
    assert cfg["add_labels"]["max"] == 1 and cfg["add_comment"]["max"] == 1
    # no write-capable safe output other than labels/comments may ever be configured
    write_types = {k for k in cfg if k not in {"noop", "missing_tool", "missing_data",
                                                "report_incomplete",
                                                "create_report_incomplete_issue", "mentions"}}
    assert write_types == {"add_labels", "add_comment"}


def test_no_closing_or_destructive_capability():
    lock = WF_LOCK.read_text()
    for forbidden in ("close_issue", "update_issue", "create_pull_request", "merge",
                      "push_to_pull_request_branch", "lock_issue", "remove_labels"):
        assert f'"{forbidden}"' not in lock, forbidden
    md = WF_MD.read_text()
    assert re.search(r"^permissions:\n  contents: read\n  issues: read\n", md, re.M)


def test_skill_scripts_match_bash_allowlist():
    md = WF_MD.read_text()
    skill = (SKILL_DIR / "SKILL.md").read_text()
    for script in ("repro_black.py", "validate_labels.py"):
        assert f"python3 .claude/skills/black-issue-triage/scripts/{script}:*" in md
        assert f"python3 .claude/skills/black-issue-triage/scripts/{script}" in skill


def test_model_is_pinned_in_lock():
    head = WF_LOCK.read_text().splitlines()[0]
    meta = json.loads(head.split("gh-aw-metadata: ", 1)[1])
    md_model = re.search(r"^  model: (\S+)$", WF_MD.read_text(), re.M).group(1)
    assert meta["agent_model"] == md_model and not md_model.endswith("latest")


# --------------------------------------------------------------------------------------
# Ground-truth isolation: the agent must never be able to read evaluation answers
# (evals/golden/ expected outcomes, analysis/need/ maintainer labels and close reasons).
GROUND_TRUTH = ("analysis", "evals", "DESIGN.md")
SCRUB_STEP = "Remove evaluation and ground-truth data from the agent workspace"


def _agent_job(lock: str) -> str:
    start = lock.index("\n  agent:\n")
    end = lock.index("\n  conclusion:\n", start)
    return lock[start:end]


def _scrub_script(job: str) -> str:
    m = re.search(rf"- name: {re.escape(SCRUB_STEP)}\n\s+run: (\".*\")\n", job)
    assert m, "scrub step missing from the compiled agent job"
    return json.loads(m.group(1))


def test_sparse_checkout_excludes_ground_truth():
    job = _agent_job(WF_LOCK.read_text())
    m = re.search(r"name: Checkout repository \(gh-aw default\)\n(?:.*\n)*?\s+sparse-checkout: \|\n"
                  r"((?:\s{12}\S.*\n)+)", job)
    assert m, "agent checkout is not sparse"
    entries = [ln.strip() for ln in m.group(1).splitlines()]
    assert entries == [".claude/", ".github/", "docs/", "src/"]
    assert not any(e.rstrip("/") in GROUND_TRUTH for e in entries)


def test_scrub_step_runs_after_checkout_and_before_agent():
    job = _agent_job(WF_LOCK.read_text())
    i_checkout = job.index("name: Checkout repository (gh-aw default)")
    i_scrub = job.index(SCRUB_STEP)
    i_prefetch = job.index("Prefetch triage context")
    i_agent = job.index("name: Execute Claude Code CLI")
    assert i_checkout < i_scrub < i_prefetch < i_agent
    # nothing may re-materialise repository files between the scrub and the agent
    between = job[i_scrub:i_agent]
    assert "actions/checkout" not in between and "git checkout" not in between
    script = _scrub_script(job)
    assert "rm -rf analysis evals DESIGN.md" in script and "exit 1" in script


def test_scrub_script_removes_paths_and_fails_closed(tmp_path):
    import subprocess

    script = _scrub_script(_agent_job(WF_LOCK.read_text()))
    (tmp_path / "analysis" / "need").mkdir(parents=True)
    (tmp_path / "analysis" / "need" / "black_issues_raw.json").write_text("{}")
    (tmp_path / "evals" / "golden").mkdir(parents=True)
    (tmp_path / "evals" / "golden" / "expected.md").write_text("answers")
    (tmp_path / "DESIGN.md").write_text("results")
    (tmp_path / "AGENTS.md").write_text("facts")
    r = subprocess.run(["bash", "-c", script], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert not any((tmp_path / p).exists() for p in GROUND_TRUTH)
    assert (tmp_path / "AGENTS.md").exists()
    # fail-closed: if a path cannot be removed, the step (and so the agent job) fails
    stuck = script.replace("rm -rf analysis evals DESIGN.md", "true")
    (tmp_path / "evals").mkdir()
    r = subprocess.run(["bash", "-c", stuck], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 1 and "evals is still present" in r.stdout


def test_user_rate_limit_compiled():
    lock = WF_LOCK.read_text()
    assert 'GH_AW_RATE_LIMIT_MAX: "3"' in lock and 'GH_AW_RATE_LIMIT_WINDOW: "60"' in lock
    events = re.search(r'GH_AW_RATE_LIMIT_EVENTS: "([^"]*)"', lock).group(1).split(",")
    assert "issues" in events
    pre = lock[lock.index("\n  pre_activation:\n"):lock.index("\n  safe_outputs:\n")]
    assert "check_rate_limit.outputs.rate_limit_ok == 'true'" in pre



def test_no_framework_authored_issues():
    """Failure/incomplete/missing-tool/detection reporting must not open or comment on issues."""
    lock = WF_LOCK.read_text()
    for flag in ("GH_AW_FAILURE_REPORT_AS_ISSUE", "GH_AW_REPORT_INCOMPLETE_CREATE_ISSUE",
                 "GH_AW_MISSING_TOOL_CREATE_ISSUE", "GH_AW_NOOP_REPORT_AS_ISSUE"):
        values = set(re.findall(rf'{flag}: "(\w+)"', lock))
        assert values == {"false"}, (flag, values)
    for step in ("handle_detection_runs.cjs", "name: Report failed jobs"):
        assert step not in lock, step
    act = lock[lock.index("\n  activation:\n"):lock.index("\n  agent:\n")]
    perms = act[act.index("    permissions:"):].split("\n    steps:", 1)[0]
    assert "issues: write" not in perms


def test_claude_engine_pinned_model_and_budgets():
    md = WF_MD.read_text()
    lock = WF_LOCK.read_text()
    assert re.search(r"^  id: claude$", md, re.M)
    md_model = re.search(r"^  model: (\S+)$", md, re.M).group(1)
    assert md_model == "claude-sonnet-5-5"
    # agent and threat-detection jobs both use the pinned model
    assert re.findall(r"ANTHROPIC_MODEL: (\S+)", lock) == [md_model, md_model]
    assert "ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}" in lock
    # $25 top-up guard (1 AIC = $0.01): worst case per run = agent + detection cap <= $1
    caps = [int(x) for x in re.findall(r'"maxAiCredits":(\d+)', lock)]
    assert sorted(caps) == [20, 70] and sum(caps) * 25 <= 2500
    assert re.search(r"^max-daily-ai-credits: (\d+)$", md, re.M).group(1) == "800"
    # no direct egress to model providers or GitHub from the agent (inference via AWF proxy)
    domains = json.loads(re.search(r'"allowDomains":(\[[^\]]*\])', lock).group(1))
    assert not [d for d in domains if "github" in d or "anthropic" in d]


def test_skill_is_discoverable():
    """Claude Code discovers project skills in .claude/skills; the checkout must include it."""
    job = _agent_job(WF_LOCK.read_text())
    assert "            .claude/\n" in job
    skill = (SKILL_DIR / "SKILL.md").read_text()
    assert skill.startswith("---\nname: black-issue-triage\n")
    assert "validate_labels.py --skill-loaded" in skill


def test_detection_skipped_for_noop_or_unsuccessful_agent():
    lock = WF_LOCK.read_text()
    det = lock[lock.index("\n  detection:\n"):]
    cond = det[det.index("    if:"):det.index("    runs-on:")]
    assert "needs.agent.result == 'success'" in cond
    assert "needs.agent.outputs.output_types != 'noop'" in cond
    # safe outputs still require a successful detection, so nothing unscreened is ever written
    so = lock[lock.index("\n  safe_outputs:\n"):]
    assert "needs.detection.result == 'success'" in so[:so.index("    runs-on:")]


def test_trusted_context_outside_agent_writable_paths():
    md, lock = WF_MD.read_text(), WF_LOCK.read_text()
    assert "TRIAGE_CONTEXT_DIR: ${{ github.workspace }}/.triage-context" in md
    assert '--out "$TRIAGE_CONTEXT_DIR" --audit-dir /tmp/gh-aw/agent/triage' in lock
    # the agent may only edit under /tmp; the context dir is in the workspace
    allowed = lock.split("--allowed-tools '\\''", 1)[1].split("'\\''", 1)[0].split(",")
    disallowed = lock.split("--disallowed-tools ", 1)[1].split(" ", 1)[0].split(",")
    edits = [t for t in allowed if t.startswith("Edit")]
    assert edits == ["Edit(//tmp/**)"] and "Write" in disallowed and "MultiEdit" in disallowed


def test_audit_artifact_excludes_virtualenvs_and_conclusion_slot_per_issue():
    lock = WF_LOCK.read_text()
    assert "!/tmp/gh-aw/agent/triage/venvs/" in lock
    assert 'group: "gh-aw-conclusion-issue-triage-${{ github.event.issue.number' in lock
    assert 'group: "gh-aw-claude-issue-triage"' in lock   # agent runs stay serialised


def test_no_pull_request_or_contents_write_anywhere():
    lock = WF_LOCK.read_text()
    assert "pull-requests: write" not in lock and "contents: write" not in lock


def test_labels_are_applied_not_suggested_and_landing_is_audited():
    lock = WF_LOCK.read_text()
    assert _handler_cfg_main(lock)["add_labels"]["issue_intent"] is False
    job = lock[lock.index("\n  verify_outputs:\n"):lock.index("\n  conclusion:\n")] \
        if lock.index("\n  verify_outputs:\n") < lock.index("\n  conclusion:\n") \
        else lock[lock.index("\n  verify_outputs:\n"):]
    assert "issues: read" in job and "write" not in job.split("steps:")[0]
    assert "AGENT_OUTPUT: ${{ needs.agent.outputs.output }}" in job


def _handler_cfg_main(lock):
    m = re.search(r'GH_AW_SAFE_OUTPUTS_HANDLER_CONFIG: "(.*)"', lock)
    return json.loads(m.group(1).encode().decode("unicode_escape"))


def test_verify_outputs_logic():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "verify_outputs", REPO_ROOT / ".github" / "scripts" / "verify_outputs.py")
    vo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vo)
    items = [{"type": "add_labels", "labels": [{"name": "spam / ai", "confidence": "MEDIUM"}, "T: bug"]},
             {"type": "add_comment", "body": "x"}]
    labels, comments = vo.requested(items)
    assert labels == ["spam / ai", "T: bug"] and comments == 1
    res = vo.compare(labels, ["T: bug"])
    assert res["applied"] == ["T: bug"] and res["not_applied"] == ["spam / ai"]
