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
# Trusted context written by the pre-agent step (issue, code blocks, release list). It lives in
# the workspace, where the agent has no Edit/Write grant, and is made read-only (chmod a-w).
DEFAULT_CONTEXT_DIR = Path(os.environ.get("TRIAGE_CONTEXT_DIR")
                           or Path(os.environ.get("GITHUB_WORKSPACE", ".")) / ".triage-context")


def resolve_dirs(triage_dir: str | None, context_dir: str | None) -> tuple[Path, Path]:
    """(work dir, context dir). An explicit --triage-dir alone means "both in one dir" (tests)."""
    work = Path(triage_dir) if triage_dir else DEFAULT_TRIAGE_DIR
    if context_dir:
        ctx = Path(context_dir)
    elif triage_dir and not os.environ.get("TRIAGE_CONTEXT_DIR"):
        ctx = work
    else:
        ctx = DEFAULT_CONTEXT_DIR
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
