#!/usr/bin/env python3
"""Replay golden cases into the sandbox and collect the agent's outputs.

All writes go ONLY to the sandbox repository below; the script refuses any other target.

  replay.py create CASE_ID [CASE_ID ...]   create the sandbox issue(s), in the given order
  replay.py collect CASE_ID RUN_ID          download logs + artifacts + `gh aw audit` for one run,
                                           save the issue's labels/comments/timeline, record cost
  replay.py run CASE_ID [CASE_ID ...]      create each issue, wait for the run it triggers, collect,
                                           and print the cumulative AI-credit total
  replay.py dispatch CASE_ID                re-run an existing case via workflow_dispatch and collect

State is kept in evals/golden/runs/mapping.json (case -> sandbox issue -> run id).
Outputs go to evals/golden/runs/<case_id>/.
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
GOLDEN = Path(__file__).resolve().parent.parent
CASES, RUNS = GOLDEN / "cases", GOLDEN / "runs"
MAPPING = RUNS / "mapping.json"


def sh(*args: str, check: bool = True) -> str:
    assert SANDBOX in " ".join(args), f"refusing non-sandbox command {args}"
    return subprocess.run(args, check=check, capture_output=True, text=True).stdout


def load_map() -> dict:
    return json.loads(MAPPING.read_text()) if MAPPING.exists() else {}


def save_map(m: dict) -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    MAPPING.write_text(json.dumps(m, indent=2) + "\n")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create(case_ids: list[str]) -> None:
    m = load_map()
    for cid in case_ids:
        if cid in m:
            print(f"{cid}: already replayed as #{m[cid]['issue']}, skipping")
            continue
        d = CASES / cid
        title = (d / "replay_title.txt").read_text().strip()
        labels = json.loads((d / "replay_labels.json").read_text())
        cmd = ["gh", "issue", "create", "-R", SANDBOX, "--title", title,
               "--body-file", str(d / "replay_body.md")]
        for lb in labels:
            cmd += ["--label", lb]
        url = sh(*cmd).strip()
        number = int(url.rsplit("/", 1)[1])
        m[cid] = {"issue": number, "url": url, "created": now(), "runs": []}
        save_map(m)
        print(f"{cid}: created #{number}")
        time.sleep(5)  # keep creation order == number order for the duplicate pool


def _usage(path: Path) -> float:
    try:
        return float(json.loads(path.read_text()).get("ai_credits") or 0)
    except (OSError, ValueError):
        return 0.0


def collect(cid: str, rid: str) -> dict:
    m = load_map()
    entry = m[cid]
    n = entry["issue"]
    out = RUNS / cid
    rdir = out / f"run_{rid}"
    rdir.mkdir(parents=True, exist_ok=True)
    for name, path in [("issue.json", f"repos/{SANDBOX}/issues/{n}"),
                       ("comments.json", f"repos/{SANDBOX}/issues/{n}/comments"),
                       ("timeline.json", f"repos/{SANDBOX}/issues/{n}/timeline?per_page=100")]:
        (out / name).write_text(sh("gh", "api", path))
    view = sh("gh", "run", "view", rid, "-R", SANDBOX, "--json",
              "databaseId,event,status,conclusion,createdAt,updatedAt,url,jobs")
    (rdir / "run_view.json").write_text(view)
    (rdir / "run.log").write_text(sh("gh", "run", "view", rid, "-R", SANDBOX, "--log", check=False))
    sh("gh", "run", "download", rid, "-R", SANDBOX, "-D", str(rdir / "artifacts"), check=False)
    audit = subprocess.run(["gh", "aw", "audit", rid, "--repo", SANDBOX, "-o", f"/tmp/awaudit/{rid}"],
                           capture_output=True, text=True, cwd="/tmp")
    (rdir / "gh_aw_audit.md").write_text(audit.stdout + audit.stderr)
    a = rdir / "artifacts"
    agent_aic = _usage(a / "agent" / "agent_usage.json")
    det_aic = _usage(a / "detection" / "detection_usage.json")
    timeline = json.loads((out / "timeline.json").read_text())
    bot_labels = [e["label"]["name"] for e in timeline if e.get("event") == "labeled"
                  and (e.get("actor") or {}).get("login") == "github-actions[bot]"]
    comments = json.loads((out / "comments.json").read_text())
    audit_log = a / "triage-audit" / "skill_audit.jsonl"
    events = [json.loads(l) for l in audit_log.read_text().splitlines()] if audit_log.exists() else []
    v = json.loads(view)
    summary = {"case": cid, "issue": n, "run": int(rid), "event": v["event"], "conclusion": v["conclusion"],
               "jobs": {j["name"]: j["conclusion"] for j in v["jobs"]},
               "agent_aic": agent_aic, "detection_aic": det_aic, "total_aic": round(agent_aic + det_aic, 3),
               "labels_added_by_bot": bot_labels,
               "bot_comments": [c["body"] for c in comments if c["user"]["login"] == "github-actions[bot]"],
               "skill_events": [e["event"] for e in events],
               "repro": [{k: e.get(k) for k in ("version", "black_args", "outcome", "source")}
                         for e in events if e["event"] == "repro"],
               "duplicate_candidates": None}
    ctx = a / "triage-audit" / "context.json"
    if ctx.exists():
        c = json.loads(ctx.read_text())
        summary["duplicate_candidates"] = [(d["number"], d["title"][:60], d["score"]) for d in c["duplicate_candidates"]]
        summary["prefetch_skip"] = c.get("skip_reason")
    (rdir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    entry.setdefault("runs", [])
    if int(rid) not in entry["runs"]:
        entry["runs"].append(int(rid))
    save_map(m)
    with open(RUNS / "costs.jsonl", "a") as fh:
        fh.write(json.dumps({"case": cid, "run": int(rid), "agent_aic": agent_aic,
                             "detection_aic": det_aic, "ts": now()}) + "\n")
    total = sum(json.loads(l)["agent_aic"] + json.loads(l)["detection_aic"]
                for l in (RUNS / "costs.jsonl").read_text().splitlines())
    print(f"{cid} #{n} run {rid}: {v['conclusion']} aic={agent_aic:.2f}+{det_aic:.2f} "
          f"labels={bot_labels} comments={len(summary['bot_comments'])} skill={summary['skill_events']} "
          f"CUMULATIVE_AIC={total:.2f} (~${total/100:.2f})")
    return summary


def _wait_for_new_run(after: str, event: str) -> str:
    for _ in range(60):
        runs = json.loads(sh("gh", "run", "list", "-R", SANDBOX, "--workflow", WORKFLOW, "--limit", "10",
                             "--json", "databaseId,event,createdAt"))
        new = [r for r in runs if r["event"] == event and r["createdAt"] >= after]
        if new:
            rid = str(sorted(new, key=lambda r: r["createdAt"])[0]["databaseId"])
            subprocess.run(["gh", "run", "watch", rid, "-R", SANDBOX, "--exit-status"],
                           capture_output=True, text=True)
            return rid
        time.sleep(10)
    raise SystemExit("no run appeared")


def run(case_ids: list[str]) -> None:
    for cid in case_ids:
        t0 = now()
        create([cid])
        collect(cid, _wait_for_new_run(t0, "issues"))


def dispatch(cid: str) -> None:
    n = load_map()[cid]["issue"]
    t0 = now()
    sh("gh", "workflow", "run", WORKFLOW, "-R", SANDBOX, "-f", f"issue_number={n}")
    collect(cid, _wait_for_new_run(t0, "workflow_dispatch"))


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "create":
        create(args)
    elif cmd == "collect":
        collect(args[0], args[1])
    elif cmd == "run":
        run(args)
    elif cmd == "dispatch":
        dispatch(args[0])
