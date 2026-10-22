#!/usr/bin/env python3
"""Tester driver for the red-team workflow: run probe sets sequentially on one target and collect evidence.

Usage: python3 -I evals/redteam/run_redteam_sets.py TARGET OUT_DIR SET [SET ...]
For each set: snapshot #1 and TARGET, dispatch issue-triage-redteam with the probe set, wait,
then save run.log, run_view.json, artifacts (minus repro venvs), `gh aw audit`, after-snapshots.
All writes target the sandbox only.
"""

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

S = "curryriiiice/black-triage-sandbox"
WF = "issue-triage-redteam.lock.yml"


def sh(*a, check=True):
    assert S in " ".join(a), a
    for i in range(4):
        try:
            r = subprocess.run(a, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            r = subprocess.CompletedProcess(a, 124, "", "timeout")
        if r.returncode == 0 or not check:
            return r.stdout
        time.sleep(15 * (i + 1))
    raise subprocess.CalledProcessError(r.returncode, a, r.stdout, r.stderr)


def snap(d: Path, n: int) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / f"issue_{n}.json").write_text(sh("gh", "api", f"repos/{S}/issues/{n}"))
    (d / f"comments_{n}.json").write_text(sh("gh", "api", f"repos/{S}/issues/{n}/comments?per_page=100"))
    (d / f"timeline_{n}.json").write_text(sh("gh", "api", f"repos/{S}/issues/{n}/timeline?per_page=100"))


def main():
    target, out, sets = int(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
    if "--reset-target" in sets:  # remove the bot's labels from the target first
        sets = [x for x in sets if x != "--reset-target"]
        tl = json.loads(sh("gh", "api", f"repos/{S}/issues/{target}/timeline?per_page=100"))
        bot = {e["label"]["name"] for e in tl if e.get("event") == "labeled"
               and (e.get("actor") or {}).get("login") == "github-actions[bot]"}
        cur = {lb["name"] for lb in json.loads(sh("gh", "api", f"repos/{S}/issues/{target}"))["labels"]}
        for lb in sorted(bot & cur):
            sh("gh", "issue", "edit", str(target), "-R", S, "--remove-label", lb)
        print("reset target: removed", sorted(bot & cur), flush=True)
    for ps in sets:
        d = out / ps
        snap(d / "before", 1), snap(d / "before", target)
        t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        sh("gh", "workflow", "run", WF, "-R", S, "-f", f"issue_number={target}", "-f", f"probe_set={ps}")
        rid = None
        for _ in range(60):
            runs = json.loads(sh("gh", "run", "list", "-R", S, "--workflow", WF, "--limit", "5",
                                 "--json", "databaseId,createdAt"))
            new = [r for r in runs if r["createdAt"] >= t0]
            if new:
                rid = str(new[-1]["databaseId"])
                break
            time.sleep(10)
        for _ in range(90):  # poll; `gh run watch` hung repeatedly during the evaluation
            if sh("gh", "run", "view", rid, "-R", S, "--json", "status", "--jq", ".status", check=False).strip() == "completed":
                break
            time.sleep(20)
        (d / "dispatched_at.txt").write_text(t0 + "\n")
        (d / "run_view.json").write_text(sh("gh", "run", "view", rid, "-R", S, "--json",
                                            "databaseId,event,status,conclusion,createdAt,updatedAt,url,jobs,headSha"))
        (d / "run.log").write_text(sh("gh", "run", "view", rid, "-R", S, "--log", check=False))
        sh("gh", "run", "download", rid, "-R", S, "-D", str(d / "artifacts"), check=False)
        shutil.rmtree(d / "artifacts" / "triage-audit" / "venvs", ignore_errors=True)
        if os.environ.get("SKIP_AW_AUDIT") != "1":
            a = subprocess.run(["gh", "aw", "audit", rid, "--repo", S, "-o", f"/tmp/awaudit/{rid}"],
                               capture_output=True, text=True, cwd="/tmp")
            (d / "gh_aw_audit.md").write_text(a.stdout + a.stderr)
        snap(d / "after", 1), snap(d / "after", target)
        v = json.loads((d / "run_view.json").read_text())
        print(ps, rid, v["conclusion"], {j["name"]: j["conclusion"] for j in v["jobs"]}, flush=True)


if __name__ == "__main__":
    main()
