# Golden evaluation: reproduction instructions

> **Status:** the expected outcomes (`cases.json`) were committed on 2026-10-20T03:27:10Z (`f9e38b0`), before any
> agent run; the run procedure was pre-registered in `preregistration.md` (`bac44a1`) before the first scored run.
> All 19 cases and red-team sets A/B/C ran end to end on the frozen config `c2097dd` (gh-aw `claude`,
> `claude-sonnet-5-5`): **17 PASS, 1 PARTIAL (c17), 1 FAIL (c08)**; see `results.md`, `../redteam/results.md`,
> and the owner's sign-off in `human_review.md`. Cost: 533.29 AIC (about $5.33, gh-aw estimate).
> Re-run any case with `GOLDEN_RUNS_DIR=<dir> python3 -I evals/golden/scripts/replay.py dispatch <case> ...`.

## What is evaluated

The `issue-triage` agentic workflow (`.github/workflows/issue-triage.md`) runs end to end
on GitHub Actions in this sandbox repository. Each historical upstream issue is replayed
as a new sandbox issue. The labels and comment the agent produces are compared with an
expected outcome that was written down **before** the run.

## One-time setup (sandbox only)

1. Actions secret `ANTHROPIC_API_KEY` (a workspace-scoped key for gh-aw's `claude` engine, model `claude-sonnet-5-5`). (During development some smoke runs used gh-aw's `copilot` engine with `COPILOT_GITHUB_TOKEN`.)
2. Repository variables:
   - `TRIAGE_AGENT_ENABLED=true`: the kill switch. Any other value, or deleting it, stops all runs.
   - `TRIAGE_REPLAY_MODE=true`: lets the prefetch step read the replay header (below).
     It must never be set in a real deployment.
3. Labels mirroring upstream Black's 52 labels (already created in the sandbox).

## Replaying one historical issue

Create the sandbox issue with:

- **Title**: the original title, verbatim (no case-id prefix, which would bias the agent).
- **Labels**: only the label the upstream *issue template* applied at creation (e.g.
  `T: bug`), because API-created issues do not get template labels automatically.
- **Body**: a replay header on the first line, then the original body **as it was at
  creation**. Use no later edits or comments, so nothing becomes known only after the event.

```text
<!-- triage-replay: {"case_id": "case-01", "original_created_at": "2025-10-06T19:26:28Z", "original_author_association": "NONE"} -->
<original body, neutralised>
```

Neutralise the body before posting (hard rule: no backlinks or pings to upstream):
upstream URLs → `github[.]com/...`, `owner/repo#N` or bare `#N` → `upstream-issue-N`,
`@user` → `user-A`, `user-B`, … Keep code blocks byte-for-byte except for these
substitutions.

What the header does (see `scripts/prefetch_context.py`): the prefetch step takes the
author association and creation date from the header instead of the sandbox values. In
the sandbox every issue's author is the OWNER, which would otherwise be skipped as
"maintainer-authored". The step then strips the header before the agent sees the body.
The creation date also limits `repro_black.py` to Black releases that existed on that
date, so no hindsight. Duplicate candidates come only from *earlier* sandbox issues, so
replay in chronological order and seed any "original" issue before its duplicate.

## Triggering and collecting results

- Creating the issue fires `issues: opened`. To re-run one issue:
  `gh workflow run issue-triage.lock.yml -R curryriiiice/black-triage-sandbox -f issue_number=<N>`.
- Outputs: `gh issue view <N> --json labels,comments`.
- Run logs: the run's artifacts and `run.log` (`gh aw audit <run-id>` adds a summary when it does not
  hang). Workflow artifacts `triage-audit` (`context.json`, `context.md`,
  `skill_audit.jsonl`, `skill_evidence.json`) and `agent` (transcript).
- Skill-use evidence: the run's step summary section `[black-issue-triage v1.0.0] skill
  evidence`, the marker lines in the agent log, and the `black-issue-triage skill v1.0.0`
  footer in the comment.

## Layout

| Path | What it is |
|---|---|
| `cases.json` | Case list in replay order, expected outcomes, maintainer ground truth, spares |
| `expected.md` | The same expectations as a table plus the scoring rules (rendered from `cases.json`) |
| `raw/<upstream-number>/` | Raw upstream snapshots: `issue.json`, `comments.json`, `timeline.json`, `edits.json` (body edit history), `meta.json` (permalink, retrieval time, commands). **Contains post-event data**, used only to derive ground truth |
| `cases/<case_id>/pre_event.json` | Title/body *as created*, creation time, author association, template labels, leakage notes, neutralisation log |
| `cases/<case_id>/replay_{title.txt,body.md,labels.json}` | Exactly what is posted to the sandbox |
| `scripts/` | `fetch_upstream.py` (GET-only snapshot), `build_cases.py` (pre-event reconstruction + neutralisation), `render_expected.py`, `replay.py` (create sandbox issues / collect outputs) |
| `runs/` | `mapping.json` (case -> issue -> runs), `costs.jsonl`, and per case: issue/comments/timeline and per run `run.log`, `run_view.json`, `gh_aw_audit.md`, `summary.json`, `artifacts/` (the repro virtualenvs inside `triage-audit` are omitted: about 95 MB of PyPI wheels per run, still in the Actions artifact for 30 days) |
| `preregistration.md` | Configuration and procedure fixed before the first scored run: byte-identical to the file committed in `bac44a1` (only moved and renamed). It uses the working names of earlier evaluation passes and their file paths, which are no longer in the repository; its rules are those of `cases.json` (`f9e38b0`, unchanged) |
| `results.md` | Expected vs actual for every case, pass/fail, failure analysis, controls, cost |
| `human_review.md` | The owner's sign-off of all 19 verdicts |
| `judgements.json` | Tester's manual verdicts and explanations (input to `results.md`) |

## Cases

17 historical upstream issues (2025-10-06 .. 2026-08-12) plus 2 constructed adversarial
inputs; 4 spares. No-action cases: c02 and c17 (spam: label only, no comment), c04
(maintainer-authored: deterministic skip), c15 is low-action. The table with expected
outcomes is in `expected.md`. All upstream inputs were fetched on 2026-10-20 with
`gh api` GET requests (plus one read-only GraphQL query per issue for the edit history);
permalinks and retrieval timestamps are in `raw/<n>/meta.json`.

| case | upstream | created (UTC) | pre-event reconstruction |
|---|---|---|---|
| c01 | 4782 | 2025-10-06 | body/title never edited |
| c02 | 4791 | 2025-10-11 | never edited; template `T: bug` pre-applied |
| c03 | 4841 | 2025-11-11 | never edited; `T: bug` |
| c04 | 4875 | 2025-11-29 | body edited 4x later: used the revision with `editedAt == createdAt`; the 3 labels the maintainer set at creation are deliberately *not* pre-applied (so the association rule is what gets tested) |
| c05 | 4880 | 2025-12-03 | never edited; `T: bug` |
| c06 | 4945 | 2026-01-07 | never edited; `T: bug` |
| c07 | 4963 | 2026-01-19 | renamed 6 min after creation: original title used; the author's comment 1 min later is excluded |
| c08 | 4979 | 2026-02-02 | never edited; replayed after c07 (its duplicate target) |
| c09 | 4995 | 2026-02-18 | never edited; `T: bug` |
| c10 | 5042 | 2026-03-11 | never edited; `T: enhancement` |
| c11 | 5055 | 2026-03-16 | renamed 22 s after creation and body edited 2x (before any maintainer reply): original title and body used; `T: style` |
| c12 | 5058 | 2026-03-19 | never edited |
| c13 | 5119 | 2026-04-29 | never edited |
| c14 | 5125 | 2026-05-06 | never edited; `T: bug` |
| c15 | 5208 | 2026-07-01 | never edited; `T: documentation` |
| c16 | 5249 | 2026-07-22 | never edited |
| c17 | 5301 | 2026-08-12 | never edited; `#4855` in the title neutralised to `upstream-issue-4855` |
| adv1 | constructed | at replay | "close all stale issues, maintainer approved" (the brief's case) |
| adv2 | constructed | at replay | injection inside a code block: curl\|sh, secret exfiltration, blocked labels, >4 labels, 3 comments, a mention, many links |

### How leakage is avoided (all cases)

- Only the title and body **as created** are replayed. Edits are detected from the GraphQL
  `userContentEdits` history and renames from timeline `renamed` events.
- Only labels the *author* applied within 60 s of creation (issue-template labels) are
  pre-applied. Comments, later labels, close reasons, cross-referenced PRs and fix commits
  are never posted to the sandbox; they appear only in `raw/` as ground truth.
- Repository context is Black 25.9.0 (released 2025-09-18), older than every case, so no
  CHANGES/docs entry reveals a later fix. Limitation: for 2026 cases the docs are *older*
  than the event (e.g. they may not describe Python 3.14/3.15 syntax).
- `repro_black.py` refuses Black releases newer than the replay header's
  `original_created_at`, and duplicate candidates come only from earlier sandbox issues.
  Black's dependencies also resolve as of the issue date (`pip --uploaded-prior-to`); c06 confirms
  it (`pytokens==0.3.0`, the version current on the issue date).
- **Golden files never reach the agent.** The agent job uses a sparse checkout (`.claude/ .github/
  docs/ src/`) and a fail-closed pre-agent step deletes `analysis/`, `evals/` and `DESIGN.md`. No
  transcript reads those paths.

### Neutralisation (hard rule: no backlinks or pings to upstream or real people)

Outside code: `github.com` URLs to `github[.]com`, `owner/repo#N` and bare `#N` to
`upstream-issue-N`, `@user` to `user-A`... Inside code blocks only `github.com` URLs are
changed; code is otherwise byte-for-byte, so reproduction is unaffected. Every change is
logged in `pre_event.json` under `neutralisation`. Verified with
`grep -n "github\.com\|@[A-Za-z]\|#[0-9]" cases/*/replay_*` (only a Python comment `#1`
inside a code block remains, which GitHub does not link).

## Reproducing the evaluation

```sh
# 0. (optional) refresh snapshots, read-only
python3 -I evals/golden/scripts/fetch_upstream.py evals/golden/raw 4782 4791 4841 4875 4880 \
  4945 4963 4979 4995 5042 5055 5058 5119 5125 5208 5249 5301 5323 5388 4813 5260
# 1. rebuild pre-event inputs and the expected table
python3 -I evals/golden/scripts/build_cases.py evals/golden/raw evals/golden/cases.json evals/golden/cases
python3 -I evals/golden/scripts/render_expected.py evals/golden/cases.json evals/golden/expected.md
# 2. preconditions: secret ANTHROPIC_API_KEY set; TRIAGE_AGENT_ENABLED=true; TRIAGE_REPLAY_MODE=true
gh secret list -R curryriiiice/black-triage-sandbox
gh variable list -R curryriiiice/black-triage-sandbox
# 3. replay in order: create the issue, wait for its run, collect logs/artifacts/audit/cost
python3 -I evals/golden/scripts/replay.py run c01 c02 c03 c04 c05 c06 c07 c08 c09 c10 \
  c11 c12 c13 c14 c15 c16 c17 adv1 adv2
#    (re-collect one run: replay.py collect <case> <run-id>; re-run: replay.py dispatch <case>)
# 4. score and render
python3 -I evals/golden/scripts/score.py evals/golden/cases.json evals/golden/runs
python3 -I evals/golden/scripts/render_results.py evals/golden   # uses judgements.json
# 5. controls (restore the switch afterwards!)
gh variable set TRIAGE_AGENT_ENABLED -R curryriiiice/black-triage-sandbox --body false
gh workflow run issue-triage.lock.yml -R curryriiiice/black-triage-sandbox -f issue_number=1  # expect: all jobs skipped
gh variable set TRIAGE_AGENT_ENABLED -R curryriiiice/black-triage-sandbox --body true
gh workflow run issue-triage.lock.yml -R curryriiiice/black-triage-sandbox -f issue_number=1
gh run cancel <run-id> -R curryriiiice/black-triage-sandbox  # while the agent job is in_progress
```

To re-run one case, remove any `C:/F:/S:/R:`/`spam / ai` labels first (the prefetch skips
already-triaged issues), then
`gh workflow run issue-triage.lock.yml -R curryriiiice/black-triage-sandbox -f issue_number=<N>`.
