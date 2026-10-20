#!/usr/bin/env python3
"""Fetch raw, read-only snapshots of upstream Black issues for the golden evaluation.

Read-only: uses `gh api` GET requests (REST) plus one read-only GraphQL *query* per issue
(no mutations) to recover the issue body's edit history, so the body *as created* can be
reconstructed. Nothing is written to GitHub.

Usage:
    python3 -I evals/golden/scripts/fetch_upstream.py OUT_DIR N [N ...]

Writes, per issue, OUT_DIR/<N>/:
    issue.json      REST issue object (current state; includes final labels: post-event!)
    comments.json   all comments (post-event data, used only for ground truth)
    timeline.json   timeline events (labels, closes, cross-references; ground truth)
    edits.json      GraphQL userContentEdits of the body (to detect post-creation edits)
    meta.json       permalink, retrieval timestamp, commands used
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

UPSTREAM = "psf/black"

GQL = """
query($owner:String!, $name:String!, $n:Int!) {
  repository(owner:$owner, name:$name) {
    issue(number:$n) {
      number createdAt lastEditedAt
      userContentEdits(first: 100) { totalCount nodes { createdAt editedAt diff } }
    }
  }
}
"""


def gh_get(path: str, paginate: bool = False):
    cmd = ["gh", "api", "-X", "GET", "-H", "Accept: application/vnd.github+json"]
    if paginate:
        cmd += ["--paginate", "--slurp"]
    cmd.append(path)
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    data = json.loads(out)
    if paginate:  # --slurp returns a list of pages
        data = [item for page in data for item in page]
    return data


def gh_graphql(n: int):
    owner, name = UPSTREAM.split("/")
    cmd = ["gh", "api", "graphql", "-f", f"query={GQL}", "-F", f"owner={owner}",
           "-F", f"name={name}", "-F", f"n={n}"]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def main() -> int:
    out_dir = Path(sys.argv[1])
    for n in map(int, sys.argv[2:]):
        d = out_dir / str(n)
        d.mkdir(parents=True, exist_ok=True)
        retrieved = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        issue = gh_get(f"repos/{UPSTREAM}/issues/{n}")
        comments = gh_get(f"repos/{UPSTREAM}/issues/{n}/comments?per_page=100", paginate=True)
        timeline = gh_get(f"repos/{UPSTREAM}/issues/{n}/timeline?per_page=100", paginate=True)
        edits = gh_graphql(n)
        for fname, obj in [("issue.json", issue), ("comments.json", comments),
                           ("timeline.json", timeline), ("edits.json", edits)]:
            (d / fname).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
        meta = {
            "upstream_issue": n,
            "permalink": issue.get("html_url"),
            "api_url": issue.get("url"),
            "retrieved_at": retrieved,
            "created_at": issue.get("created_at"),
            "closed_at": issue.get("closed_at"),
            "commands": [
                f"gh api -X GET repos/{UPSTREAM}/issues/{n}",
                f"gh api -X GET --paginate --slurp repos/{UPSTREAM}/issues/{n}/comments",
                f"gh api -X GET --paginate --slurp repos/{UPSTREAM}/issues/{n}/timeline",
                "gh api graphql (read-only query: issue.userContentEdits)",
            ],
        }
        (d / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(f"{n}: created {meta['created_at']} comments={len(comments)} "
              f"timeline={len(timeline)} edits={edits['data']['repository']['issue']['userContentEdits']['totalCount']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
