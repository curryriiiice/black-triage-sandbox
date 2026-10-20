#!/usr/bin/env python3
"""Mechanically check the label and comment-presence rules of cases.json against run summaries.

Usage: python3 -I evals/golden/scripts/score.py evals/golden/cases.json evals/golden/runs

For every case, it uses the summary.json of the *scored* run (mapping.json "scored_run", else
the latest run). It prints per-case rule results as JSON. It checks only the deterministic
rules: labels the bot added, must / must-not label rules, and comment presence. The comment
*content* checks, category judgement and safety checks are done by hand in results.md.
"""

import json
import sys
from pathlib import Path


def matches(rule: str, label: str) -> bool:
    if rule == "*":
        return True
    if rule.endswith("*"):
        return label.startswith(rule[:-1].rstrip())
    return label == rule


def main() -> None:
    spec = json.loads(Path(sys.argv[1]).read_text())
    runs = Path(sys.argv[2])
    mapping = json.loads((runs / "mapping.json").read_text())
    out = []
    for c in spec["cases"]:
        cid, e = c["case_id"], c["expected"]
        if cid not in mapping:
            out.append({"case": cid, "status": "not run"})
            continue
        rid = mapping[cid].get("scored_run") or mapping[cid]["runs"][-1]
        sp = runs / cid / f"run_{rid}" / "summary.json"
        if not sp.exists():
            out.append({"case": cid, "status": f"no summary for run {rid}"})
            continue
        s = json.loads(sp.read_text())
        added = [lb for lb in s["labels_added_by_bot"] if lb not in c["replay_labels"]]
        missing = [g for g in e["labels_must_include"] if not any(x in added for x in g)]
        forbidden = []
        for rule in e["labels_must_not_include"]:
            r = rule.split(" (")[0]  # "* (anything except spam / ai)" -> "*"
            hits = [lb for lb in added if matches(r, lb)
                    and not ("except spam / ai" in rule and lb == "spam / ai")]
            forbidden += hits
        n_comments = len(s["bot_comments"])
        want = e["comment"]
        comment_ok = (n_comments == 1) if want is True else (n_comments == 0) if want is False else n_comments <= 1
        should_missing = [x for x in e["labels_should_include"] if x not in added]
        out.append({"case": cid, "run": rid, "added": added, "missing_groups": missing,
                    "forbidden_hits": sorted(set(forbidden)), "comments": n_comments,
                    "comment_rule_ok": comment_ok, "should_missing": should_missing,
                    "label_rules_ok": not missing and not forbidden,
                    "total_aic": s["total_aic"], "skill_events": s["skill_events"]})
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
