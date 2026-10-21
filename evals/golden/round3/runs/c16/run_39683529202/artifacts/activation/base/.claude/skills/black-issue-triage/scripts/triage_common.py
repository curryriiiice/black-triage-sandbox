"""Shared helpers for the black-issue-triage skill scripts.

Standard library only: the scripts run on a bare GitHub-hosted runner and inside the
gh-aw agent sandbox, where nothing beyond CPython is guaranteed.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
from pathlib import Path
from typing import Any

SKILL_NAME = "black-issue-triage"
SKILL_VERSION = "1.0.0"
# Printed by every script so skill use is visible in the agent transcript / Actions logs.
MARKER = f"[{SKILL_NAME} v{SKILL_VERSION}]"

# Agent-writable work dir: audit log and throw-away repro virtualenvs.
DEFAULT_TRIAGE_DIR = Path(os.environ.get("TRIAGE_DIR", "/tmp/gh-aw/agent/triage"))
# Fixed work dir under GitHub Actions (no CLI or env override).
ACTIONS_WORK_DIR = Path("/tmp/gh-aw/agent/triage")
# The trusted context (issue, code blocks, release list) is written by the pre-agent prefetch to
# $GITHUB_WORKSPACE/.triage-context: no agent Edit/Write grant there, chmod a-w, and under Actions
# the scripts accept no other location (see resolve_dirs).


def resolve_dirs(triage_dir: str | None, context_dir: str | None) -> tuple[Path, Path]:
    """(work dir, context dir).

    Under GitHub Actions (GITHUB_ACTIONS=true, i.e. in the agent sandbox) command-line overrides
    are IGNORED: the agent could otherwise point the scripts at a context it wrote itself under
    /tmp (e.g. a fake release list), bypassing the hindsight guard. The context dir must then be
    exactly `$GITHUB_WORKSPACE/.triage-context` (the read-only prefetch output); anything else
    fails closed. Outside Actions (local runs, unit tests) an explicit --triage-dir alone means
    "both in one dir".
    """
    if os.environ.get("GITHUB_ACTIONS") == "true":
        workspace = os.environ.get("GITHUB_WORKSPACE")
        if not workspace:
            raise SystemExit(f"{MARKER} GITHUB_WORKSPACE is not set; refusing to run")
        trusted = (Path(workspace) / ".triage-context").resolve()
        ctx = Path(os.environ.get("TRIAGE_CONTEXT_DIR") or trusted).resolve()
        if ctx != trusted:
            raise SystemExit(f"{MARKER} context dir {ctx} is not the trusted {trusted}; refusing")
        if triage_dir or context_dir:
            print(f"{MARKER} note: --triage-dir/--context-dir are ignored under GitHub Actions")
        return ACTIONS_WORK_DIR.resolve(), ctx
    work = Path(triage_dir) if triage_dir else DEFAULT_TRIAGE_DIR
    if context_dir:
        ctx = Path(context_dir)
    elif triage_dir and not os.environ.get("TRIAGE_CONTEXT_DIR"):
        ctx = work
    else:
        ctx = Path(os.environ.get("TRIAGE_CONTEXT_DIR")
                   or Path(os.environ.get("GITHUB_WORKSPACE", ".")) / ".triage-context")
    return work.resolve(), ctx.resolve()


SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = SKILL_DIR / "config"

# Author associations that GitHub reports for people with write access or org membership.
MAINTAINER_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}

# Replay header used only when TRIAGE_REPLAY_MODE=true (sandbox evaluation). It lets a
# historical issue that was re-created by the sandbox owner carry its *original* metadata.
REPLAY_HEADER_RE = re.compile(r"<!--\s*triage-replay:\s*(\{.*?\})\s*-->", re.DOTALL)


def utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def audit(triage_dir: Path, event: str, **fields: Any) -> None:
    """Append one JSON line to the skill audit log (uploaded as a workflow artifact)."""
    triage_dir.mkdir(parents=True, exist_ok=True)
    record = {"ts": utcnow_iso(), "skill": SKILL_NAME, "version": SKILL_VERSION, "event": event}
    record.update(fields)
    with open(triage_dir / "skill_audit.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def load_label_policy() -> dict[str, Any]:
    policy = load_json(CONFIG_DIR / "label_policy.json")
    if policy is None:
        raise SystemExit(f"{MARKER} ERROR: cannot read {CONFIG_DIR / 'label_policy.json'}")
    return policy


_VERSION_RE = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?$")


def parse_version(v: str) -> tuple[int, int, int] | None:
    """Parse a final-release Black version like '25.9.0' or '22.1'. Pre-releases -> None."""
    m = _VERSION_RE.match(v.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
