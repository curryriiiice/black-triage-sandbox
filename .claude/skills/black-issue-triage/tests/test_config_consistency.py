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
