# Measured need: data and scripts

These are GET-only GitHub API reads of upstream Black, fetched 2026-10-20 (UTC). Nothing was
written upstream. They back the numbers in `DESIGN.md` section 1.

| File | What |
|---|---|
| `fetch_black_issues.py` | fetches issues created in a window, plus every comment and event (`gh api`, GET) |
| `black_issues_raw.json` | output for 2025-10-01..2026-09-30 (91 issues, matching the live search `total_count`) |
| `analyze_black_need.py` | response-time and triage-action metrics; unanswered issues are right-censored at the as-of date |
| `black_need_metrics.json` | output (`summary.external` = 80 non-maintainer, non-bot authors) |
| `analyze_black_extra.py` | closure/label concentration, spam share, open-backlog labelling |
| `black_open_issues_2026-10-20.json` | all open issues on 2026-10-20 (PRs filtered in the script) |
| `black_need_extra.json` | output |
| `black_labels.txt` | upstream label names and descriptions (mirrored into the sandbox) |

Reproduce (Python 3.10+, no dependencies):

```bash
python3 -I fetch_black_issues.py 2025-10-01 2026-09-30 black_issues_raw.json   # needs gh auth
python3 -I analyze_black_need.py black_issues_raw.json 2026-10-20 black_need_metrics.json
python3 -I analyze_black_extra.py black_issues_raw.json black_open_issues_2026-10-20.json black_need_extra.json
```

The second command was re-run on 2026-10-20 and reproduces `black_need_metrics.json` exactly.
Definitions and limitations are in the script docstrings and `DESIGN.md`.
