# black-triage-sandbox

A sandbox for evaluating an **AI first-pass issue-triage agent** for the
[_Black_](https://github.com/psf/black) code formatter. It runs as a GitHub Agentic Workflow
(gh-aw) with the GitHub Copilot engine. The code under `src/`, `tests/` and `docs/` is a copy of
upstream Black **25.9.0** (MIT licence, `LICENSE`; authors in `AUTHORS.md`; upstream README
in `UPSTREAM_README.md`). This repository is not affiliated with the Black project, and
nothing here is sent upstream.

## Deliverables

| What | Where |
|---|---|
| Agentic workflow (source / compiled) | `.github/workflows/issue-triage.md`, `.github/workflows/issue-triage.lock.yml` |
| Repository facts for agents | `AGENTS.md` |
| Claude Skill (procedure + scripts + tests) | `.claude/skills/black-issue-triage/` (`SKILL.md`, `scripts/`, `config/label_policy.json`, `references/`, `tests/`) |
| AI-contribution policy | `CONTRIBUTING.md` |
| Review ownership | `.github/CODEOWNERS` |
| Deterministic CI for the skill and config drift | `.github/workflows/skill-tests.yml` |
| Golden evaluation (inputs, expected, actual, logs) | `evals/golden/` (start with `evals/golden/README.md`) |
| Design justification, governance, bill of materials | `DESIGN.md` |

## How it works (one paragraph)

When an issue is opened, a deterministic step (`scripts/prefetch_context.py`) fetches it,
skips maintainer or bot issues and issues that are already triaged, extracts code blocks,
and ranks earlier issues as duplicate candidates. The Copilot agent then follows `SKILL.md`. It
classifies the issue, reproduces formatting bugs by installing the *reported* Black release
from PyPI (`scripts/repro_black.py`, which never executes the reporter's code), and
validates its labels (`scripts/validate_labels.py`). It can then add up to 4 allow-listed
labels and post at most one comment. It has no way to close, edit, lock or delete anything.

## Operating it

- Engine secret: `COPILOT_GITHUB_TOKEN` (fine-grained PAT with Copilot Requests: read).
- Kill switch: repository variable `TRIAGE_AGENT_ENABLED` must equal `true`. Set it to
  anything else to stop all runs. Cancel in-flight runs from the Actions tab.
- Manual (re-)triage: `gh workflow run issue-triage.lock.yml -f issue_number=<N>`.
- Recompile after editing the workflow: `gh aw compile issue-triage` (gh-aw v0.92.0).
