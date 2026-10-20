#!/usr/bin/env python3
"""Validate a proposed label set before the agent emits the add_labels safe output.

Checks that need no judgement: the label exists in the repository, the agent is allowed
to apply it (config/label_policy.json), mutually exclusive labels are not combined, a
duplicate label names a real candidate, and repro-backed labels match a recorded repro.

Usage:
  python3 .claude/skills/black-issue-triage/scripts/validate_labels.py "C: crash" "F: fmtskip"
  python3 .../validate_labels.py "R: duplicate" --duplicate-of 12

Exit code 0 = OK (use `final_labels` from the JSON output), 1 = fix the errors and rerun.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from triage_common import DEFAULT_TRIAGE_DIR, MARKER, audit, load_json, load_label_policy  # noqa: E402

REPRO_OUTCOME_FOR = {
    "C: crash": {"crash", "not_equivalent", "invalid_code"},
    "C: unstable formatting": {"unstable"},
    "C: invalid code": {"invalid_code", "not_equivalent"},
}


def repro_outcomes(triage_dir: Path) -> set[str]:
    path = triage_dir / "skill_audit.jsonl"
    outcomes: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("event") == "repro" and rec.get("outcome"):
                outcomes.add(rec["outcome"])
    return outcomes


def validate(labels: list[str], ctx: dict[str, Any] | None, policy: dict[str, Any],
             outcomes: set[str], duplicate_of: int | None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    ctx = ctx or {}
    repo_labels = set(ctx.get("repo_labels") or [])
    existing = set((ctx.get("issue") or {}).get("existing_labels") or [])
    allowed = set(policy["agent_may_apply"])
    maint = set(policy["maintainer_only"])

    proposed = list(dict.fromkeys(lb.strip() for lb in labels if lb.strip()))
    final: list[str] = []
    for lb in proposed:
        if lb in maint:
            errors.append(f"'{lb}' is a maintainer decision; suggest it in the comment instead")
        elif lb not in allowed:
            errors.append(f"'{lb}' is not in the agent label allow-list")
        elif repo_labels and lb not in repo_labels:
            errors.append(f"'{lb}' does not exist in this repository")
        elif lb in existing:
            warnings.append(f"'{lb}' is already on the issue; dropped")
        else:
            final.append(lb)

    if len(final) > policy["max_new_labels"]:
        errors.append(f"{len(final)} new labels; at most {policy['max_new_labels']} allowed")
    for ex in policy["exclusive_labels"]:
        if ex in final and len(final) > 1:
            errors.append(f"'{ex}' must be applied on its own")
    for prefix in policy["single_choice_prefixes"]:
        new = [lb for lb in final if lb.startswith(prefix)]
        old = [lb for lb in existing if lb.startswith(prefix)]
        if len(new) > 1:
            errors.append(f"more than one '{prefix}' label proposed: {new}")
        elif new and old:
            warnings.append(f"issue already has {old}; adding {new} leaves two type labels "
                            "(the agent cannot remove labels) - explain this in the comment")
    for lb in policy["requires_duplicate_target"]:
        if lb in final:
            cands = {c["number"] for c in ctx.get("duplicate_candidates") or []}
            if duplicate_of is None:
                errors.append(f"'{lb}' needs --duplicate-of <issue number>")
            elif duplicate_of not in cands:
                errors.append(f"#{duplicate_of} is not one of the prefetched duplicate "
                              f"candidates {sorted(cands)}")
    for lb in policy["repro_backed_labels"]:
        if lb in final and not (outcomes & REPRO_OUTCOME_FOR.get(lb, set())):
            warnings.append(f"'{lb}' is not backed by a repro_black.py result "
                            f"(recorded outcomes: {sorted(outcomes) or 'none'}); say so in the "
                            "comment or add 'S: needs repro' instead")
    if "S: needs repro" in final and outcomes & {"crash", "unstable", "invalid_code",
                                                 "not_equivalent"}:
        warnings.append("a repro already reproduced the problem; 'S: needs repro' contradicts it")
    if not final and not errors:
        warnings.append("no new labels; if no action is needed call noop instead of add_labels")
    return {"marker": MARKER, "ok": not errors, "final_labels": final, "errors": errors,
            "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate proposed triage labels.")
    ap.add_argument("labels", nargs="*")
    ap.add_argument("--duplicate-of", type=int)
    ap.add_argument("--skill-loaded", action="store_true",
                    help="record that the agent loaded SKILL.md (step 0) and exit")
    ap.add_argument("--triage-dir", default=str(DEFAULT_TRIAGE_DIR))
    ns = ap.parse_args(argv)
    triage_dir = Path(ns.triage_dir)
    if ns.skill_loaded:
        audit(triage_dir, "skill_loaded", engine=os.environ.get("GH_AW_ENGINE_ID")
              or os.environ.get("GH_AW_INFO_ENGINE_ID"))
        print(f"{MARKER} skill loaded")
        return 0
    ctx = load_json(triage_dir / "context.json")
    if ctx is None:
        print(f"{MARKER} warning: no context.json; repository label checks skipped")
    res = validate(ns.labels, ctx, load_label_policy(), repro_outcomes(triage_dir),
                   ns.duplicate_of)
    audit(triage_dir, "validate_labels", proposed=ns.labels, duplicate_of=ns.duplicate_of,
          ok=res["ok"], final_labels=res["final_labels"], errors=res["errors"])
    print(f"{MARKER} label validation: {'OK' if res['ok'] else 'FAILED'}")
    print(json.dumps(res, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
