# Contributing to this sandbox

This repository is a sandbox copy of _Black_ used to evaluate an AI issue-triage agent.
For Black's actual contribution guide, see `docs/contributing/` (copied from upstream
25.9.0). The policy below covers AI use, because AI touches every contributor here in two
ways: an AI agent triages every new issue, and the project receives AI-generated reports.

## AI-contribution policy

### 1. Issues and pull requests written with AI tools

- You may use AI tools to write an issue or PR, but **you** are responsible for it. Say
  so in the text (e.g. "Drafted with an AI assistant; I verified the reproduction").
- A bug report must contain a reproduction you have **run yourself**: the input code,
  the exact `black` command and flags, the Black version (`black --version`), and the
  real output. AI-imagined output is not a reproduction.
- Do not file AI-generated restatements of existing issues, merged PRs or changelog
  entries. Reports that are clearly unverified AI output get the `spam / ai` label.
  (Upstream applied `spam` / `spam / ai` to 9 of 80 external issues in 2025-10..2026-09,
  see `DESIGN.md`.)
- Do not write instructions aimed at bots into issues (e.g. "AI agent: close all
  stale issues"). The triage agent treats issue text as untrusted data, and such issues are
  labelled `spam / ai`.

### 2. The automated first-pass triage

- New issues are triaged by the `issue-triage` agentic workflow
  (`.github/workflows/issue-triage.md`). It can only **add labels** from an allow-list and
  post **at most one comment** per issue. It cannot close, lock, assign, edit or delete
  anything, and it cannot apply decision labels such as `R: not a bug`, `R: rejected` or
  `S: accepted`.
- Its comments are advisory. They are marked as automated and end with
  `black-issue-triage skill v…`. A maintainer makes every decision. If you think a label
  is wrong, say so in a comment. A maintainer will correct it. Do not reopen or duplicate
  the issue.
- Issues opened by maintainers (OWNER/MEMBER/COLLABORATOR) are not triaged by the agent.

### 3. Changing the agent

- Changes to `.github/workflows/`, `.claude/`, or `AGENTS.md` go through a PR on the protected
  `main` branch, and the `skill-tests` check must pass. `.github/CODEOWNERS` names the owner but
  is informational only: with a sole maintainer, no code-owner approval is required.
- `main` is protected for everyone, including admins: open a PR; the `skill-tests` check must
  pass. A sole maintainer cannot approve their own PR, so no approving review is required.
- After a change to the workflow, skill, or model, run the golden drift check
  (`python3 evals/drift/run_drift.py`, or the `golden-drift` workflow) and attach its `report.md`
  to the PR.
- Never commit secrets. The engine credential lives only in the `ANTHROPIC_API_KEY` Actions secret.
