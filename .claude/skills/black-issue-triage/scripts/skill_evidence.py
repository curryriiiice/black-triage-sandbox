#!/usr/bin/env python3
"""Summarise skill usage for the GitHub Actions step summary (runs after the agent).

Reads the triage dir written by prefetch_context.py and the skill scripts, writes
skill_evidence.json next to it, and prints a Markdown summary on stdout. It never fails
the job: missing evidence is reported, not raised.

Usage: python3 skill_evidence.py <work dir> [<context dir>]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from triage_common import MARKER, load_json  # noqa: E402


def summarise(triage_dir: Path, context_dir: Path | None = None) -> dict:
    records = []
    log = triage_dir / "skill_audit.jsonl"
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                records.append(json.loads(line))
            except ValueError:
                pass
    ctx = load_json((context_dir or triage_dir) / "context.json", {}) or {}
    counts = Counter(r.get("event") for r in records)
    agent_events = (counts.get("repro", 0) + counts.get("validate_labels", 0)
                    + counts.get("skill_loaded", 0))
    validations = [r for r in records if r.get("event") == "validate_labels"]
    return {
        "issue": (ctx.get("issue") or {}).get("number"),
        "skipped_before_agent": bool(ctx.get("skip")),
        "skip_reason": ctx.get("skip_reason"),
        "event_counts": dict(counts),
        "agent_ran_skill_scripts": agent_events > 0,
        "skill_loaded_marker": counts.get("skill_loaded", 0) > 0,
        "repro_outcomes": [r.get("outcome") for r in records if r.get("event") == "repro"],
        "last_validation": validations[-1] if validations else None,
    }


def main(argv: list[str]) -> int:
    triage_dir = Path(argv[1] if len(argv) > 1 else "/tmp/gh-aw/agent/triage")
    context_dir = Path(argv[2]) if len(argv) > 2 else None
    s = summarise(triage_dir, context_dir)
    try:
        (triage_dir / "skill_evidence.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    except OSError:
        pass
    lv = s["last_validation"] or {}
    print(f"## {MARKER} skill evidence\n")
    print(f"- issue: {s['issue']}")
    print(f"- skipped deterministically before the agent: {s['skipped_before_agent']}"
          + (f" ({s['skip_reason']})" if s["skip_reason"] else ""))
    print(f"- skill script events: {s['event_counts'] or 'none'}")
    print(f"- skill loaded (step 0 marker): {s['skill_loaded_marker']}")
    print(f"- agent invoked skill scripts: {s['agent_ran_skill_scripts']}")
    print(f"- repro outcomes: {s['repro_outcomes'] or 'none'}")
    print(f"- last label validation: ok={lv.get('ok')} labels={lv.get('final_labels')}")
    if not s["skipped_before_agent"] and not s["agent_ran_skill_scripts"]:
        print("\n> WARNING: the agent ran but no skill script was invoked; check whether the "
              "skill was loaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
