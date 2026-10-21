#!/usr/bin/env python3
"""Tester driver for red-team v2: run probe sets sequentially on one target and collect evidence.

Usage: python3 -I evals/redteam/run_redteam_sets.py TARGET OUT_DIR SET [SET ...]
For each set: snapshot #1 and TARGET, dispatch issue-triage-redteam with the probe set, wait,
then save run.log, run_view.json, artifacts (minus repro venvs), `gh aw audit`, after-snapshots.
All writes target the sandbox only.
"""

import datetime as dt
import json
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
        r = subprocess.run(a, capture_output=True, text=True)
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
        subprocess.run(["gh", "run", "watch", rid, "-R", S], capture_output=True)
        (d / "dispatched_at.txt").write_text(t0 + "\n")
        (d / "run_view.json").write_text(sh("gh", "run", "view", rid, "-R", S, "--json",
                                            "databaseId,event,status,conclusion,createdAt,updatedAt,url,jobs,headSha"))
        (d / "run.log").write_text(sh("gh", "run", "view", rid, "-R", S, "--log", check=False))
        sh("gh", "run", "download", rid, "-R", S, "-D", str(d / "artifacts"), check=False)
        shutil.rmtree(d / "artifacts" / "triage-audit" / "venvs", ignore_errors=True)
        a = subprocess.run(["gh", "aw", "audit", rid, "--repo", S, "-o", f"/tmp/awaudit/{rid}"],
                           capture_output=True, text=True, cwd="/tmp")
        (d / "gh_aw_audit.md").write_text(a.stdout + a.stderr)
        snap(d / "after", 1), snap(d / "after", target)
        v = json.loads((d / "run_view.json").read_text())
        print(ps, rid, v["conclusion"], {j["name"]: j["conclusion"] for j in v["jobs"]}, flush=True)


if __name__ == "__main__":
    main()
