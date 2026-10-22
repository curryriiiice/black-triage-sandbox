#!/usr/bin/env python3
"""Post-run audit: did the requested safe outputs actually land on the issue?

Reads the agent's *validated* safe-output items (env AGENT_OUTPUT, the agent job's `output`)
and compares them with the issue's real labels and bot comments (GitHub REST, read-only).
Writes a Markdown table to the step summary and emits a ::warning:: for every requested label
that is not on the issue (e.g. recorded as a *suggestion* instead of applied), so a green
`safe_outputs` job can no longer hide unapplied labels. Never fails the run.

Env: AGENT_OUTPUT, TARGET (issue number), GH_TOKEN, REPO, GITHUB_STEP_SUMMARY.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys


def gh_json(path: str):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else None


def requested(items: list[dict]) -> tuple[list[str], int]:
    labels, comments = [], 0
    for it in items:
        if it.get("type") == "add_labels":
            for lb in it.get("labels") or []:
                labels.append(lb["name"] if isinstance(lb, dict) else str(lb))
        elif it.get("type") == "add_comment":
            comments += 1
    return labels, comments


def compare(req_labels: list[str], issue_labels: list[str]) -> dict:
    applied = [lb for lb in req_labels if lb in issue_labels]
    missing = [lb for lb in req_labels if lb not in issue_labels]
    return {"requested": req_labels, "applied": applied, "not_applied": missing}


def main() -> int:
    raw = os.environ.get("AGENT_OUTPUT") or "{}"
    try:
        items = (json.loads(raw) or {}).get("items") or []
    except ValueError:
        items = []
    req_labels, req_comments = requested(items)
    repo, target = os.environ.get("REPO", ""), os.environ.get("TARGET", "")
    issue = gh_json(f"repos/{repo}/issues/{target}") or {}
    labels_now = [lb["name"] for lb in issue.get("labels", [])]
    res = compare(req_labels, labels_now)
    lines = ["## Safe-output landing check (requested vs applied)", "",
             f"- issue: #{target}", f"- labels requested: {res['requested'] or 'none'}",
             f"- labels applied: {res['applied'] or 'none'}",
             f"- labels NOT applied: {res['not_applied'] or 'none'}",
             f"- comments requested: {req_comments}"]
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    for lb in res["not_applied"]:
        print(f"::warning::requested label '{lb}' is not on issue #{target} (suggested or rejected)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
