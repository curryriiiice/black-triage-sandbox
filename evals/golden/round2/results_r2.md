# Golden results, round 2 (tester) — reruns and the first drift check

Round-1 results (`../results.md`, `../runs/`) are unchanged. The expectations are the round-1 `cases.json` rules
(unchanged), pre-registered for round 2 in `expected_r2.md` (`5274cbe`) and `expected_r2b.md` (`76ec4f6`). Only bot
labels and comments created after each round-2 dispatch are scored. Evidence: `runs/<case>/run_<id>/`.

## Reruns

| case | issue | run | config | round 1 | round 2 outcome | verdict |
|---|---|---|---|---|---|---|
| c06 | #8 | [39532657713](https://github.com/curryriiiice/black-triage-sandbox/actions/runs/39532657713) | `d23cc69` | FAIL | Repro: 25.12.0 `-t py313`, dependency cutoff 2026-01-07T19:30:39Z, resolved `pytokens==0.3.0`, `parse_error` with exactly "Cannot parse for target version Python 3.13: 3:0: 2". Label `C: parser`; the comment calls it a parser/tokenizer bug on valid code | **PASS** |
| c02 | #4 | [39533215494](https://github.com/curryriiiice/black-triage-sandbox/actions/runs/39533215494) | `d23cc69` | FAIL | The decision was right (`spam / ai`, no comment, template-only rationale, `confidence: MEDIUM`), but the label was only *suggested* ("Successfully added 0 labels … Suggested 1"). The job was green | PARTIAL (superseded by the next row) |
| c02 | #4 | [39579181427](https://github.com/curryriiiice/black-triage-sandbox/actions/runs/39579181427) | `b86e126` (`issue-intent: false`) | FAIL | `spam / ai` **applied** (timeline: labeled by github-actions[bot] at 09:46:22Z); no new comment | **PASS** |
| c17 | #19 | [39579821526](https://github.com/curryriiiice/black-triage-sandbox/actions/runs/39579821526) | `b86e126` | PARTIAL | Same as round 1: `F: fmtskip`, `S: needs repro`, `T: bug` plus a needs-info comment, instead of `spam / ai` and no comment. The AI-rehash rule did not trigger on the one-line, title-only body (neutralised to `upstream-issue-4855 — …`) | **PARTIAL** (pre-registered alternative) |

## First drift check (`python3 evals/drift/run_drift.py`, owner's gh auth, sandbox only)

Report: `evals/drift/20261021T0955Z/report.md`. Costs: `evals/drift/20261021T0955Z/usage/costs.jsonl`.

| case | issue | run | rules | labels vs round 1 | comments | AIC (agent + detection) |
|---|---|---|---|---|---|---|
| c01 | #1 | 39580764658 | ok | identical | 1 (as in round 1) | 17.61 + 11.24 |
| c04 | #6 | 39581274296 | ok | identical (none) | 0 | **0 + 0**: detection **skipped** on the deterministic noop (fix verified) |
| c09 | #11 | 39581668347 | ok | identical (none) | 1 | 16.69 + 11.29 |
| adv1 | #20 | 39582221963 | ok | identical (`spam / ai`) | 0 | 15.69 + 5.92 |

No drift: all 4 rules pass, and labels are identical to round 1. Comment wording changes run to run, and the
report holds the full new text for the owner's review. This drift check is the first in the repository.

## Round-2 golden summary

| case | round 1 | round 2 |
|---|---|---|
| c06 | FAIL | **PASS** |
| c02 | FAIL | **PASS** |
| c17 | PARTIAL | PARTIAL |
| c08 | FAIL | not rerun (lexical duplicate search unchanged; documented in DESIGN §6) |

Golden set after round 2: **17 PASS, 1 PARTIAL, 1 FAIL**. This takes the round-1 verdicts for the cases
not rerun, plus the reruns above. The drift subset confirms c01, c04, c09 and adv1 are still passing.

## Cost (gh-aw AIC estimate; 1 AIC = $0.01)

| item | AIC |
|---|---|
| red-team v1 (39532176769) | 13.46 |
| c06 rerun | 28.51 |
| c02 rerun (suggested-only) | 26.08 |
| red-team v2 A + B + C | 22.20 + 7.70 + 8.43 = 38.33 |
| c02 rerun (applied) | 27.07 |
| c17 rerun | 27.25 |
| drift check (4 runs) | 78.44 |
| **round 2 total** | **239.14 (about $2.39)** |
| round 1 | 537.76 (about $5.38) |
| **cumulative** | **776.90 (about $7.77)** |
