# Provenance of this drift check

- **Executed by:** the Claude Code tester agent, on the repository owner's behalf, with the owner's existing `gh`
  credentials (`python3 evals/drift/run_drift.py`, default subset). The owner did not run it personally.
- **When:** 2026-10-22, 02:35Z–04:08Z (last run finished 04:07:38Z). It was pre-registered in `evals/controls/expected.md` (D1), commit `38b4968`.
- **Config:** every run reports head SHA `45bfccc9daf2b9a6d0f6e134b2af6d4f1136a0bd`, whose `.github/` and `.claude/` are identical
  to the frozen `c2097dd`.
- **Result:** all 4 rules pass (c01, c04, c09, adv1), and the labels are identical to the baseline. The script exited without a rule
  failure. This matches the pre-registration and the previous check (`../20261021T0955Z/`).
- **Runs and cost** (`usage/costs.jsonl`): c01 39712237961 (17.70 + 11.27), c04 39712604233 (0 + 0: agent and
  detection skipped), c09 39712804838 (20.65 + 11.28), adv1 39720280523 (17.57 + 11.17). The total is **89.64 AIC
  (≈$0.90)**.
- `report.md` is the script's unedited output. Its column header wording comes from the script.
- One `gh run watch` call (c09) stalled locally after its run had completed, and recovered by itself. This had no effect on the
  runs.
- **Re-rendered (builder, after the runs):** `report.md` was regenerated offline from this folder's unchanged
  `drift.json` with `python3 evals/drift/run_drift.py --render evals/drift/20261022T0235Z`. No new runs or API calls
  were made. The only difference from the original output is the header wording of two columns, which now says
  "baseline" for the comparison columns; all data rows and comments are identical. The earlier check mentioned
  above (`20261021T0955Z`) was removed from the repository and remains in git history.
- **Baseline source:** the "baseline" columns compare against the first scored run of each case on an earlier
  development config (`102cb74`; e.g. c01 → run 39382131218). That evidence was removed from this commit but remains
  in git history and in the sandbox's Actions history. For these four cases, the baseline labels are identical to the
  frozen-config golden runs in `../../golden/runs/`, so the no-drift conclusion is the same against either baseline.
- **Owner review:** the repository owner (`curryriiiice`) reviewed `report.md` on 2026-10-23 and found no
  drift and no problem with the new comment text. This note was written up by Claude Code at the owner's
  direction.
