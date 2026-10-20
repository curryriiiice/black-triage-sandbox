#!/usr/bin/env python3
"""Build leakage-free, neutralised replay inputs from the raw upstream snapshots.

Usage:
    python3 -I evals/golden/scripts/build_cases.py evals/golden/raw evals/golden/cases.json evals/golden/cases

For each case listed in cases.json this writes evals/golden/cases/<case_id>/:
    pre_event.json   title/body *as created*, created_at, author association,
                     template labels, and the leakage-avoidance notes
    replay_body.md   the exact body posted to the sandbox (replay header + neutralised body)
    replay_title.txt the exact title posted to the sandbox (neutralised)

Pre-event reconstruction (no hindsight):
  * body: if the GraphQL edit history is non-empty, the revision whose editedAt equals the
    issue's createdAt is the body at creation; otherwise the current body is unedited.
  * title: if the timeline contains `renamed` events, the `from` of the earliest rename.
  * labels: only labels the *author* applied within 60 s of creation (issue-template labels).
  * nothing from comments, later labels, closes, cross-references or fix commits is used.

Neutralisation (shared hard rule: no backlinks/pings to upstream or real people), applied
outside fenced code blocks and inline code spans (where GitHub would autolink):
  github.com URLs -> github[.]com ; owner/repo#N and bare #N -> upstream-issue-N ;
  @user -> user-A, user-B, ... Code blocks are kept byte-for-byte except github.com URLs
  (-> github[.]com), so reproduction is unaffected.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

FENCE_SPLIT = re.compile(r"(^(?:```+|~~~+)[^\n]*\n.*?^(?:```+|~~~+)[ \t]*$)", re.DOTALL | re.MULTILINE)
INLINE_SPLIT = re.compile(r"(`+[^`\n]*`+)")
URL_GH = re.compile(r"(https?://)(?:www\.)?github\.com", re.IGNORECASE)
REPO_REF = re.compile(r"\b[\w.-]+/[\w.-]+#(\d+)\b")
BARE_REF = re.compile(r"(?<![\w&/])#(\d+)\b")
MENTION = re.compile(r"(?<![\w`/.])@([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))\b")


def _iso(s: str) -> dt.datetime:
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


class Neutraliser:
    def __init__(self) -> None:
        self.users: dict[str, str] = {}
        self.log: list[str] = []

    def _user(self, m: re.Match) -> str:
        name = m.group(1)
        if name not in self.users:
            self.users[name] = f"user-{chr(ord('A') + len(self.users))}"
        self.log.append(f"@{name} -> {self.users[name]}")
        return self.users[name]

    def _prose(self, text: str) -> str:
        out = []
        for part in INLINE_SPLIT.split(text):
            if part.startswith("`"):
                out.append(part)
                continue
            new = URL_GH.sub(lambda m: m.group(1) + "github[.]com", part)
            new = REPO_REF.sub(lambda m: f"upstream-issue-{m.group(1)}", new)
            new = BARE_REF.sub(lambda m: f"upstream-issue-{m.group(1)}", new)
            new = MENTION.sub(self._user, new)
            if new != part:
                self.log.append(f"prose changed: {part.strip()[:80]!r}")
            out.append(new)
        return "".join(out)

    def run(self, text: str) -> str:
        parts = FENCE_SPLIT.split(text or "")
        return "".join(self._code(p) if FENCE_SPLIT.fullmatch(p) else self._prose(p)
                       for p in parts)

    def _code(self, block: str) -> str:
        # Inside code GitHub creates no links or mentions, so code is kept byte-for-byte,
        # except github.com URLs (hard rule: never write upstream URLs to GitHub).
        new = URL_GH.sub(lambda m: m.group(1) + "github[.]com", block)
        if new != block:
            self.log.append("code block: github.com URL neutralised")
        return new


def body_at_creation(issue: dict, edits: dict) -> tuple[str, str]:
    nodes = edits["data"]["repository"]["issue"]["userContentEdits"]["nodes"]
    if not nodes:
        return issue.get("body") or "", "no edits recorded; current body == body at creation"
    for node in nodes:
        if node.get("editedAt") == issue["created_at"]:
            return node.get("diff") or "", (
                f"{len(nodes) - 1} later edit(s); used the revision with editedAt == createdAt")
    raise SystemExit(f"cannot reconstruct original body of {issue['number']}")


def title_at_creation(issue: dict, timeline: list) -> tuple[str, str]:
    renames = sorted((e for e in timeline if e.get("event") == "renamed"),
                     key=lambda e: e["created_at"])
    if renames:
        return renames[0]["rename"]["from"], (
            f"renamed {len(renames)}x later; used the earliest rename's `from`")
    return issue["title"], "never renamed; current title == title at creation"


def template_labels(issue: dict, timeline: list) -> list[str]:
    created, author = _iso(issue["created_at"]), issue["user"]["login"]
    out = []
    for e in timeline:
        if e.get("event") == "labeled" and (e.get("actor") or {}).get("login") == author:
            if (_iso(e["created_at"]) - created).total_seconds() <= 60:
                out.append(e["label"]["name"])
    return out


def main() -> int:
    raw, spec_path, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    for case in spec["cases"]:
        if case.get("kind") == "adversarial":
            continue
        n = case["upstream_issue"]
        issue = json.loads((raw / str(n) / "issue.json").read_text(encoding="utf-8"))
        timeline = json.loads((raw / str(n) / "timeline.json").read_text(encoding="utf-8"))
        edits = json.loads((raw / str(n) / "edits.json").read_text(encoding="utf-8"))
        body, body_note = body_at_creation(issue, edits)
        title, title_note = title_at_creation(issue, timeline)
        tlabels = template_labels(issue, timeline)
        neut = Neutraliser()
        n_title, n_body = neut.run(title), neut.run(body.replace("\r\n", "\n"))
        assoc = issue["author_association"]
        header = {"case_id": case["case_id"], "original_created_at": issue["created_at"],
                  "original_author_association": assoc}
        d = out / case["case_id"]
        d.mkdir(parents=True, exist_ok=True)
        pre = {
            "case_id": case["case_id"], "upstream_issue": n, "permalink": issue["html_url"],
            "created_at": issue["created_at"], "author_association": assoc,
            "title_at_creation": title, "body_at_creation": body,
            "template_labels_detected": tlabels,
            "replay_labels": case["replay_labels"],
            "leakage_avoidance": [
                title_note, body_note,
                "labels: only author-applied template labels within 60 s of creation",
                "excluded: all comments, later labels, close reason, cross-referenced PRs/commits",
                "repo context: sandbox snapshot is Black 25.9.0 (2025-09-18), older than the case",
                "repro: repro_black.py refuses Black releases newer than original_created_at",
            ],
            "neutralisation": neut.log,
        }
        (d / "pre_event.json").write_text(json.dumps(pre, indent=2, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
        (d / "replay_title.txt").write_text(n_title + "\n", encoding="utf-8")
        (d / "replay_labels.json").write_text(json.dumps(case["replay_labels"]) + "\n",
                                              encoding="utf-8")
        (d / "replay_body.md").write_text(
            f"<!-- triage-replay: {json.dumps(header)} -->\n{n_body}\n", encoding="utf-8")
        print(f"{case['case_id']} upstream {n}: detected={tlabels} replay={case['replay_labels']} edits='{body_note[:30]}' "
              f"title='{title_note[:25]}' neutralised={len(neut.log)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
