"""The red-team workflow must exercise exactly the production controls.

`issue-triage-redteam.md` may differ from `issue-triage.md` only in: its trigger (manual
dispatch, sandbox repo only), descriptive metadata, its budget (turns/credits), one extra
pre-approved command (`curl`, so that the *network firewall* has to stop egress), and its
prompt. Everything that enforces behaviour (permissions, engine/model, network allow-list,
safe outputs, checkout, scrub/prefetch steps, detection gate, env) must be identical, both in
the frontmatter and in the compiled lock files.
"""

import json
import re

from conftest import REPO_ROOT

WF = REPO_ROOT / ".github" / "workflows"
PROD_MD, RT_MD = WF / "issue-triage.md", WF / "issue-triage-redteam.md"
PROD_LOCK, RT_LOCK = WF / "issue-triage.lock.yml", WF / "issue-triage-redteam.lock.yml"
MAY_DIFFER = {"description", "intent", "tracker-id", "on", "if", "max-turns", "max-ai-credits"}


def _frontmatter_blocks(path):
    text = path.read_text()
    fm = text[4:text.index("\n---\n", 4)]
    blocks, key = {}, None
    for line in fm.splitlines():
        m = re.match(r"^([a-z][a-z0-9-]*):", line)
        if m:
            key = m.group(1)
            blocks[key] = [line]
        elif key:
            blocks[key].append(line)
    return {k: "\n".join(ln for ln in v if not ln.strip().startswith("#")).strip()
            for k, v in blocks.items()}


def test_frontmatter_controls_identical():
    prod, rt = _frontmatter_blocks(PROD_MD), _frontmatter_blocks(RT_MD)
    assert set(prod) == set(rt)
    for key in sorted(set(prod) - MAY_DIFFER):
        if key == "tools":
            extra = [ln for ln in rt[key].splitlines() if ln not in prod[key].splitlines()]
            assert extra == ['    - "curl:*"'], extra
            assert [ln for ln in prod[key].splitlines() if ln not in rt[key].splitlines()] == []
        else:
            assert prod[key] == rt[key], key


def test_redteam_is_dispatch_only_and_sandbox_only():
    rt = _frontmatter_blocks(RT_MD)
    assert "workflow_dispatch:" in rt["on"] and "issues:" not in rt["on"]
    assert "github.repository == 'curryriiiice/black-triage-sandbox'" in rt["if"]
    assert "vars.TRIAGE_AGENT_ENABLED == 'true'" in rt["if"]


def _handler_cfg(lock):
    m = re.search(r'GH_AW_SAFE_OUTPUTS_HANDLER_CONFIG: "(.*)"', lock)
    return json.loads(m.group(1).encode().decode("unicode_escape"))


def _job_permissions(lock):
    perms = {}
    for m in re.finditer(r"\n  ([a-z_]+):\n(?:    .*\n)*?    permissions:\n((?:      .*\n)+)", lock):
        perms[m.group(1)] = sorted(m.group(2).split("\n"))
    return perms


def test_compiled_enforcement_identical():
    prod, rt = PROD_LOCK.read_text(), RT_LOCK.read_text()
    assert _handler_cfg(prod) == _handler_cfg(rt)
    dom = r'"allowDomains":(\[[^\]]*\])'
    assert re.findall(dom, prod) == re.findall(dom, rt)
    assert _job_permissions(prod) == _job_permissions(rt)
    assert re.findall(r"ANTHROPIC_MODEL: (\S+)", prod) == re.findall(r"ANTHROPIC_MODEL: (\S+)", rt)
    for marker in ("Remove evaluation and ground-truth data", "Prefetch triage context",
                   "sparse-checkout: |", "needs.agent.outputs.output_types != 'noop'"):
        assert marker in prod and marker in rt, marker


def test_redteam_file_is_generated_from_production():
    import subprocess
    import sys
    gen = REPO_ROOT / "evals" / "redteam" / "make_redteam_workflow.py"
    r = subprocess.run([sys.executable, str(gen), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, "run evals/redteam/make_redteam_workflow.py and gh aw compile"
