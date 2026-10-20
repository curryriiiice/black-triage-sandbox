"""Read-only fetch of GitHub issues (default psf/black; override with env REPO=owner/name) created in a date window, plus their
comments and issue events, via the `gh api` CLI (GET requests only).

Usage: python -I fetch_black_issues.py START END OUTFILE
  e.g. python -I fetch_black_issues.py 2025-10-01 2026-09-30 ../ideator_data/black_issues_raw.json
"""
import json, subprocess, sys, time

import os
REPO = os.environ.get("REPO", "psf/black")

def gh(path):
    for attempt in range(5):
        p = subprocess.run(["gh", "api", "--paginate", "--slurp", path],
                           capture_output=True, text=True)
        if p.returncode == 0:
            pages = json.loads(p.stdout)
            out = []
            for pg in pages:
                out.extend(pg["items"] if isinstance(pg, dict) and "items" in pg else pg)
            return out
        sys.stderr.write(f"retry {path}: {p.stderr[:200]}\n")
        time.sleep(20 * (attempt + 1))
    raise SystemExit(f"failed: {path}")

def main(start, end, outfile):
    # Search API caps at 1000 results; window is well under that.
    q = f"repo:{REPO}+is:issue+created:{start}..{end}"
    issues = gh(f"search/issues?q={q}&per_page=100&sort=created&order=asc")
    records = []
    for it in issues:
        n = it["number"]
        comments = gh(f"repos/{REPO}/issues/{n}/comments?per_page=100")
        events = gh(f"repos/{REPO}/issues/{n}/events?per_page=100")
        records.append({
            "number": n, "title": it["title"], "user": it["user"]["login"],
            "user_type": it["user"]["type"], "author_association": it["author_association"],
            "created_at": it["created_at"], "closed_at": it["closed_at"],
            "state": it["state"], "state_reason": it.get("state_reason"),
            "labels_now": [l["name"] for l in it["labels"]],
            "comments": [{"user": c["user"]["login"], "user_type": c["user"]["type"],
                          "assoc": c["author_association"], "created_at": c["created_at"]}
                         for c in comments],
            "events": [{"event": e["event"], "actor": (e.get("actor") or {}).get("login"),
                        "actor_type": (e.get("actor") or {}).get("type"),
                        "label": (e.get("label") or {}).get("name"),
                        "created_at": e["created_at"]} for e in events],
        })
        time.sleep(0.3)
    meta = {"repo": REPO, "window": [start, end],
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "count": len(records)}
    json.dump({"meta": meta, "issues": records}, open(outfile, "w"), indent=1)
    print(meta)

if __name__ == "__main__":
    main(*sys.argv[1:4])
