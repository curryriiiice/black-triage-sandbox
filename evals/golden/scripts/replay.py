#!/usr/bin/env python3
"""Replay golden cases into the sandbox and collect the agent's outputs.

All writes go ONLY to the sandbox repository below; the script refuses any other target.

  replay.py create CASE_ID [CASE_ID ...]   create the sandbox issue(s), in the given order
  replay.py collect CASE_ID [CASE_ID ...]  find the triage run, download logs + artifacts,
                                           and save the issue's labels/comments/timeline

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
    assert SANDBOX in " ".join(args) or args[:2] == ("gh", "aw"), f"refusing non-sandbox command {args}"
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


def collect(case_ids: list[str]) -> None:
    m = load_map()
    runs = json.loads(sh("gh", "run", "list", "-R", SANDBOX, "--workflow", WORKFLOW,
                         "--limit", "100", "--json",
                         "databaseId,event,status,conclusion,createdAt,displayTitle,url"))
    for cid in case_ids:
        entry = m[cid]
        n = entry["issue"]
        out = RUNS / cid
        out.mkdir(parents=True, exist_ok=True)
        issue = json.loads(sh("gh", "api", f"repos/{SANDBOX}/issues/{n}"))
        comments = json.loads(sh("gh", "api", f"repos/{SANDBOX}/issues/{n}/comments"))
        timeline = json.loads(sh("gh", "api", f"repos/{SANDBOX}/issues/{n}/timeline?per_page=100"))
        for name, obj in [("issue.json", issue), ("comments.json", comments),
                          ("timeline.json", timeline)]:
            (out / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
        title = issue["title"]
        mine = [r for r in runs if r["displayTitle"] == title
                or r["displayTitle"].endswith(f"#{n}") or str(n) in r["displayTitle"]]
        entry["runs"] = sorted({r["databaseId"] for r in mine} | set(entry.get("runs", [])))
        for rid in entry["runs"]:
            rdir = out / f"run_{rid}"
            rdir.mkdir(exist_ok=True)
            (rdir / "run_view.json").write_text(sh(
                "gh", "run", "view", str(rid), "-R", SANDBOX, "--json",
                "databaseId,event,status,conclusion,createdAt,updatedAt,url,jobs"))
            (rdir / "run.log").write_text(sh("gh", "run", "view", str(rid), "-R", SANDBOX,
                                             "--log", check=False))
            sh("gh", "run", "download", str(rid), "-R", SANDBOX, "-D", str(rdir / "artifacts"),
               check=False)
        save_map(m)
        print(f"{cid}: #{n} runs={entry['runs']} labels={[l['name'] for l in issue['labels']]} "
              f"comments={len(comments)}")


if __name__ == "__main__":
    {"create": create, "collect": collect}[sys.argv[1]](sys.argv[2:])
