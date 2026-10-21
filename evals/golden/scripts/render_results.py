#!/usr/bin/env python3
"""Render evals/golden/results.md from cases.json, runs/*/summary.json, score.py rules and the
tester's manual judgements (evals/golden/judgements.json).

Usage: python3 -I evals/golden/scripts/render_results.py evals/golden

judgements.json: {"<case_id>": {"verdict": "PASS|PARTIAL|FAIL|NOT RUN", "category": "<actual cat>",
                                "explanation": "..."}}
"""

import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    g = Path(sys.argv[1])
    # optional: RUNS_DIR JUDGEMENTS OUT TITLE (defaults: round 1 layout)
    runs = Path(sys.argv[2]) if len(sys.argv) > 2 else g / "runs"
    jpath = Path(sys.argv[3]) if len(sys.argv) > 3 else g / "judgements.json"
    outp = Path(sys.argv[4]) if len(sys.argv) > 4 else g / "results.md"
    spec = json.loads((g / "cases.json").read_text())
    mapping = json.loads((runs / "mapping.json").read_text())
    judg = json.loads(jpath.read_text())
    score = {r["case"]: r for r in json.loads(subprocess.run(
        [sys.executable, "-I", str(g / "scripts" / "score.py"), str(g / "cases.json"), str(runs)],
        capture_output=True, text=True, check=True).stdout)}
    rows, counts, aic = [], {}, 0.0
    for c in spec["cases"]:
        cid, e = c["case_id"], c["expected"]
        j = judg.get(cid, {"verdict": "NOT RUN", "category": "-", "explanation": "not run"})
        counts[j["verdict"]] = counts.get(j["verdict"], 0) + 1
        s = score.get(cid, {})
        m = mapping.get(cid, {})
        rid = s.get("run", "-")
        issue = m.get("issue")
        actual_labels = ", ".join(f"`{x}`" for x in s.get("added", [])) or "none"
        comment = {0: "no comment", 1: "1 comment"}.get(s.get("comments"), f"{s.get('comments', '-')} comments")
        aic += s.get("total_aic", 0) or 0
        exp = (f"{e['category']}; labels must incl. "
               + (" AND ".join("/".join(gr) for gr in e["labels_must_include"]) or "none")
               + f"; comment={e['comment']}")
        run_link = f"[{rid}](https://github.com/curryriiiice/black-triage-sandbox/actions/runs/{rid})" if rid != "-" else "-"
        rows.append(f"| {cid} | {c['upstream_issue'] or 'constructed'} | {'#'+str(issue) if issue else '-'} | {run_link} | "
                    f"{exp} | {j['category']}: {actual_labels}; {comment} | **{j['verdict']}** | {j['explanation']} |")
    head = ["# Golden evaluation results (round 1)", "",
            "Expected outcomes were committed before any run (`f9e38b0`, 2026-10-20T03:27:10Z). Engine: gh-aw",
            "`claude`, model `claude-sonnet-5-5` (pinned), Claude Code 2.1.296, sandbox main `102cb74`.",
            "Labels are those the bot added (template labels pre-applied at replay are excluded).",
            "The scoring rules are in `expected.md`. Label/comment-count rules are checked by `scripts/score.py`;",
            "comment content, category and safety checks were judged by the tester (`judgements.json`).",
            "", "**Counts:** " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())),
            f"  \n**AI credits (scored runs, agent + detection):** {aic:.2f} AIC (about ${aic/100:.2f}).",
            "", "| case | upstream | sandbox | run | expected | actual | verdict | explanation |",
            "|---|---|---|---|---|---|---|---|"]
    if len(sys.argv) > 4:
        head[0] = "# Golden evaluation results (round 3: full rerun on the frozen config)"
        head[2:4] = ["Expected outcomes: `cases.json` (unchanged), pre-registered for round 3 in `round3/expected_r3.md`.",
                     "Engine gh-aw `claude`, model `claude-sonnet-5-5` (pinned), frozen sandbox main `c2097dd`."]
    outp.write_text("\n".join(head + rows) + "\n")
    print(counts, round(aic, 2))


if __name__ == "__main__":
    main()
