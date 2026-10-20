# Golden evaluation: reproduction instructions

> Status: **harness contract written by the builder (round 1)**. The tester fills in the
> case files, expected outcomes, actual outputs and logs, and extends this README with the
> exact commands they ran. Sections marked `TODO(tester)` are not done yet.

## What is evaluated

The `issue-triage` agentic workflow (`.github/workflows/issue-triage.md`) runs end to end
on GitHub Actions in this sandbox repository. Each historical upstream issue is replayed
as a new sandbox issue. The labels and comment the agent produces are compared with an
expected outcome that was written down **before** the run.

## One-time setup (sandbox only)

1. Actions secret `ANTHROPIC_API_KEY` (the engine credential gh-aw's `claude` engine needs).
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
- Run logs: `gh aw logs issue-triage` and `gh aw audit <run-id>` (model, turns, tool calls,
  firewall log, AI credits). Workflow artifacts `triage-audit` (`context.json`, `context.md`,
  `skill_audit.jsonl`, `skill_evidence.json`) and `agent` (transcript).
- Skill-use evidence: the run's step summary section `[black-issue-triage v1.0.0] skill
  evidence`, the marker lines in the agent log, and the `black-issue-triage skill v1.0.0`
  footer in the comment.

## Cases

TODO(tester): case table (id, upstream reference, snapshot of context, expected outcome
recorded before the run, actual output, pass/fail, explanation), the adversarial case(s),
and the raw logs.
