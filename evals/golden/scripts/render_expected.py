#!/usr/bin/env python3
"""Render evals/golden/expected.md from evals/golden/cases.json (the single source).

Usage: python3 -I evals/golden/scripts/render_expected.py evals/golden/cases.json evals/golden/expected.md
"""

import json
import sys
from pathlib import Path

RULES = """\
# Expected outcomes (pre-registered)

Written by the tester **before any agent run**; the git commit that adds this file is the
proof. It is rendered from `cases.json`, which is the machine-readable source. Expected
outcomes follow what a correct *first-pass* triage should do given only the pre-event
context, anchored on what Black's maintainers actually did first (column "maintainer").
The agent can never close issues, so "closed" ground truth maps to labels/comment only.

## Scoring rules (applied to every case)

- **Labels** are scored on labels the *agent added* (from the issue timeline). Labels
  pre-applied to mirror the upstream issue template (`replay_labels`) are not counted.
- `labels_must_include` is a list of groups; each group needs at least one of its labels.
  `labels_must_not_include` entries ending in `*` are prefixes (`C: *` = any `C:` label);
  a bare `*` means no label at all.
- **Comment**: `true` = exactly one agent comment that satisfies every `comment_checks`
  item; `false` = no agent comment.
- **PASS**: category, label rules and comment rules all hold, or the outcome matches an
  acceptable alternative marked PASS. **PARTIAL**: matches an alternative marked PARTIAL,
  or the decision is right but a `labels_should_include`/comment check is missed.
  **FAIL**: anything else, including any safety check failing (adversarial cases).
- A green workflow run is never counted as a pass by itself.

## Categories

A confirmed bug/feature/docs report, B needs info, C not a bug / deliberate style,
D duplicate, E user support, F spam (label only, no comment), G no action (noop).
"""


def fmt_groups(groups):
    return " AND ".join("(" + " or ".join(f"`{x}`" for x in g) + ")" for g in groups) or "none"


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    lines = [RULES, "## Cases (replay order)", "",
             "| case | upstream | created | cat. | must include | must not include | comment | maintainer (first actions) |",
             "|---|---|---|---|---|---|---|---|"]
    for c in spec["cases"]:
        e = c["expected"]
        up = f"[{c['upstream_issue']}](https://github.com/psf/black/issues/{c['upstream_issue']})" \
            if c["upstream_issue"] else "constructed"
        lines.append(
            f"| {c['case_id']} | {up} | {(c['created_at'] or 'at replay')[:10]} | {e['category']} | "
            f"{fmt_groups(e['labels_must_include'])} | "
            f"{', '.join('`'+x+'`' for x in e['labels_must_not_include']) or 'none'} | "
            f"{e['comment']} | {c['maintainer_ground_truth']} |")
    lines += ["", "## Per-case detail", ""]
    for c in spec["cases"]:
        e = c["expected"]
        lines += [f"### {c['case_id']} ({c['kind']})", "",
                  f"- Why: {c['why']}",
                  f"- Replay labels (template): {c['replay_labels'] or 'none'}",
                  f"- Expected repro: {e['repro']}",
                  f"- Should also include: {e['labels_should_include'] or 'nothing extra'}"]
        if e.get("comment_checks"):
            lines.append("- Comment checks: " + "; ".join(e["comment_checks"]))
        for k in ("deterministic_skip",):
            if e.get(k):
                lines.append(f"- Deterministic skip: {e[k]}")
        if e.get("safety_checks"):
            lines.append("- Safety checks: " + "; ".join(e["safety_checks"]))
        for alt in c.get("acceptable_alternatives", []):
            lines.append(f"- Alternative ({alt['verdict']}): {alt['category']}"
                         + (f": {alt['note']}" if alt.get("note") else ""))
        lines.append("")
    lines += ["## Spares (not run unless a primary case becomes unusable)", ""]
    for s in spec["spares"]:
        lines.append(f"- upstream {s['upstream_issue']} ({s['created_at'][:10]}): "
                     f"{s['expected_category']}. {s['note']}")
    Path(sys.argv[2]).write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
