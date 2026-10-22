#!/usr/bin/env python3
"""Golden drift check: re-run a small fixed subset of golden cases and diff against cases.json.

For each case in SUBSET it (1) removes the labels the bot added to that case's existing sandbox
replay issue (otherwise the prefetch skips it as "already triaged"), (2) re-dispatches
issue-triage for that issue (same issue number, so the duplicate pool is the same earlier
issues as in the original replay), (3) waits for the run, and (4) applies the deterministic
rules of `evals/golden/cases.json` (must / must-not labels, comment presence) to the labels and
comments the bot produced *after* the dispatch. It writes `evals/drift/<stamp>/report.md` with
the rule results, the label diff against the baseline scored run in `evals/golden/runs`, and the new comment text, and
it exits 1 if any rule fails, so a scheduled run shows up as a failed workflow.

Who reviews: the repository owner (sole maintainer) reads report.md, in particular every case
whose rule status or labels changed, and the full text of every new comment. Rule checks only
cover labels and comment presence; comment quality is the owner's judgement.

Cost: about 29 AIC (~$0.29) per model run; the default subset (c01, c04, c09, adv1) is ~3 model
runs plus one deterministic skip, so ~90 AIC (~$0.90) per drift check.

Usage: python3 evals/drift/run_drift.py [CASE ...]
       python3 evals/drift/run_drift.py --render evals/drift/<stamp>   (offline re-render)     (needs `gh` authenticated as a human
       maintainer of the sandbox: a dispatch by github-actions would be dropped by skip-bots)
All writes go only to the sandbox repository.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

SANDBOX = "curryriiiice/black-triage-sandbox"
WORKFLOW = "issue-triage.lock.yml"
ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "evals" / "golden"
SUBSET = ["c01", "c04", "c09", "adv1"]   # crash repro, deterministic skip, not-a-bug, injection
BOT = "github-actions[bot]"


def sh(*args: str) -> str:
    assert SANDBOX in " ".join(args), f"refusing non-sandbox command {args}"
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def matches(rule: str, label: str) -> bool:
    rule = rule.split(" (")[0]
    if rule == "*":
        return True
    return label.startswith(rule[:-1].rstrip()) if rule.endswith("*") else label == rule


def score(case: dict, added: list[str], n_comments: int) -> dict:
    e = case["expected"]
    added = [lb for lb in added if lb not in case["replay_labels"]]
    missing = [g for g in e["labels_must_include"] if not any(x in added for x in g)]
    forbidden = sorted({lb for r in e["labels_must_not_include"] for lb in added
                        if matches(r, lb) and not ("except spam / ai" in r and lb == "spam / ai")})
    want = e["comment"]
    comment_ok = (n_comments == 1) if want is True else (n_comments == 0) if want is False \
        else n_comments <= 1
    return {"added": added, "missing_groups": missing, "forbidden_hits": forbidden,
            "comments": n_comments, "ok": not missing and not forbidden and comment_ok}


def bot_labels_after(n: int, since: str) -> list[str]:
    tl = json.loads(sh("gh", "api", f"repos/{SANDBOX}/issues/{n}/timeline?per_page=100"))
    return [e["label"]["name"] for e in tl if e.get("event") == "labeled"
            and (e.get("actor") or {}).get("login") == BOT and e.get("created_at", "") >= since]


def bot_comments_after(n: int, since: str) -> list[str]:
    cs = json.loads(sh("gh", "api", f"repos/{SANDBOX}/issues/{n}/comments?per_page=100"))
    return [c["body"] for c in cs if c["user"]["login"] == BOT and c["created_at"] >= since]


def reset_issue(n: int) -> None:
    """Remove labels the bot added, so the prefetch does not skip the issue as triaged."""
    tl = json.loads(sh("gh", "api", f"repos/{SANDBOX}/issues/{n}/timeline?per_page=100"))
    current = {lb["name"] for lb in json.loads(sh("gh", "api", f"repos/{SANDBOX}/issues/{n}"))["labels"]}
    for lb in sorted({e["label"]["name"] for e in tl if e.get("event") == "labeled"
                      and (e.get("actor") or {}).get("login") == BOT} & current):
        sh("gh", "issue", "edit", str(n), "-R", SANDBOX, "--remove-label", lb)


def wait_run(after: str) -> str:
    for _ in range(90):
        runs = json.loads(sh("gh", "run", "list", "-R", SANDBOX, "--workflow", WORKFLOW,
                             "--limit", "10", "--json", "databaseId,event,createdAt"))
        new = [r for r in runs if r["event"] == "workflow_dispatch" and r["createdAt"] >= after]
        if new:
            rid = str(sorted(new, key=lambda r: r["createdAt"])[0]["databaseId"])
            subprocess.run(["gh", "run", "watch", rid, "-R", SANDBOX], capture_output=True)
            return rid
        time.sleep(10)
    raise SystemExit("no run appeared")


def baseline(cid: str, mapping: dict) -> dict:
    rid = mapping[cid].get("scored_run") or mapping[cid]["runs"][-1]
    s = json.loads((GOLDEN / "runs" / cid / f"run_{rid}" / "summary.json").read_text())
    return {"run": rid, "labels": s["labels_added_by_bot"], "comments": len(s["bot_comments"])}


def render_report(rows: list[dict], stamp: str) -> str:
    """report.md from the rows recorded in drift.json (no API calls)."""
    lines = [f"# Golden drift check {stamp}", "", "Reviewer: repository owner. Review every changed "
             "row and the full text of every new comment.", "",
             "| case | run | rules ok | labels now | labels baseline | comments now/baseline |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['case']} | {r['run']} | {'yes' if r['ok'] else '**NO**'} | "
                     f"{r['added']} | {r['baseline']['labels']} | {r['comments']}/"
                     f"{r['baseline']['comments']} |")
    for r in rows:
        for c in r["new_comments"]:
            lines += ["", f"## {r['case']} new comment", "", c]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if argv[:1] == ["--render"]:   # re-render report.md from an existing drift.json, offline
        d = Path(argv[1])
        rows = json.loads((d / "drift.json").read_text())
        (d / "report.md").write_text(render_report(rows, d.name))
        print(f"re-rendered {d}/report.md from drift.json")
        return 0
    subset = argv or SUBSET
    cases = {c["case_id"]: c for c in json.loads((GOLDEN / "cases.json").read_text())["cases"]}
    mapping = json.loads((GOLDEN / "runs" / "mapping.json").read_text())
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%MZ")
    out = ROOT / "evals" / "drift" / stamp
    out.mkdir(parents=True, exist_ok=True)
    rows, failed = [], False
    for cid in subset:
        n = mapping[cid]["issue"]
        reset_issue(n)
        t0 = now()
        sh("gh", "workflow", "run", WORKFLOW, "-R", SANDBOX, "-f", f"issue_number={n}")
        rid = wait_run(t0)
        labels, comments = bot_labels_after(n, t0), bot_comments_after(n, t0)
        res = score(cases[cid], labels, len(comments))
        base = baseline(cid, mapping)
        failed |= not res["ok"]
        rows.append({"case": cid, "issue": n, "run": rid, **res, "baseline": base,
                     "new_comments": comments})
        print(f"{cid}: run {rid} ok={res['ok']} labels={res['added']} comments={res['comments']}")
    (out / "drift.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    (out / "report.md").write_text(render_report(rows, stamp))
    print(f"wrote {out.relative_to(ROOT)}/report.md")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
