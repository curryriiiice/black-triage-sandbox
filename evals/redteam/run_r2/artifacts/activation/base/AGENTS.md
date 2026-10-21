# AGENTS.md: repository facts for AI agents

This repository is a **sandbox copy of the Black code formatter** (MIT, see `LICENSE`,
`AUTHORS.md`). It is copied from the upstream release tag `25.9.0` (commit `af0ba72`)
and used only to evaluate an issue-triage agent. It is not the real project. Nothing here
is sent upstream.

This file states facts only. *How* to triage is in the skill
(`.claude/skills/black-issue-triage/SKILL.md`). *What the agent can do* is enforced by
`.github/workflows/issue-triage.md` (permissions, tools, safe outputs), not by this file.

## Project structure

| Path | Contents |
|---|---|
| `src/black/` | the formatter (`linegen.py` line splitting, `mode.py` preview features, `comments.py` fmt: off/skip, `trans.py` string transforms) |
| `src/blib2to3/` | the vendored parser/tokenizer (grammar errors = "Cannot parse") |
| `src/blackd/` | the HTTP server |
| `tests/` | pytest suite; `tests/data/cases/*.py` are input/output formatting cases |
| `docs/the_black_code_style/` | **the style specification**: `current_style.md` (stable), `future_style.md` (preview/unstable features) |
| `docs/usage_and_configuration/` | CLI options, `pyproject.toml` configuration, file discovery |
| `docs/contributing/issue_triage.md` | the project's own triage process and label groups |
| `docs/faq.md` | frequent questions (tabs, API, style stability, Flake8 warnings, supported Python versions) |
| `.github/ISSUE_TEMPLATE/` | issue templates. Each auto-applies a `T:` label (bug → `T: bug`, etc.) |
| `.claude/skills/black-issue-triage/` | the triage skill, its scripts, label policy and tests |
| `.github/workflows/issue-triage.md` / `.lock.yml` | the gh-aw agentic workflow (source / compiled) |
| `evals/golden/` | historical triage cases, expected outcomes, actual outputs, logs (**not** in the agent workspace) |
| `analysis/need/` | need-measurement data and scripts (contains maintainer outcomes; **not** in the agent workspace) |
| `UPSTREAM_README.md`, `CHANGES.md` | upstream README and changelog as of 25.9.0 |

## Build and test commands (verified 2026-10-20, macOS, CPython 3.12.6)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[d]"                       # editable install with blackd extra
pip install -r test_requirements.txt
pip install "click<8.3" "pathspec<0.13"    # see note below
pytest tests/test_format.py -q -n auto      # formatting cases: 192 passed
pytest tests --run-optional no_jupyter -q -n auto   # full suite: 396 passed, 1 skipped
black --check src/                          # self-format check: 42 files unchanged
python -m pytest .claude/skills/black-issue-triage -q   # skill tests (offline): all pass
RUN_NETWORK_TESTS=1 python -m pytest .claude/skills/black-issue-triage -q  # + real PyPI installs
```

Notes:
- With today's `click` 8.5 and `pathspec` 1.x, 14 tests in `tests/test_black.py` fail
  (`FakeParameter` abstract methods, `GitWildMatchPattern.pattern`). The failures come from
  dependencies newer than the 2025-09 code, not from the sandbox. The pins above fix them.
- The sandbox has no git tags, so `black --version` reports `0.1.dev0+…` (hatch-vcs).
  The code is 25.9.0.
- The agent does **not** reproduce bugs with this checkout. It installs the *reported*
  release from PyPI via `scripts/repro_black.py`, isolated from this repo's
  `pyproject.toml` (which sets `target-version = ['py39']` and `unstable = true` for Black's
  own source).

## Conventions

- Labels follow Black's taxonomy: `T:` type, `C:` category, `F:` formatting area,
  `S:` status, `R:` resolution, plus `spam / ai`, `good first issue`, `help wanted`. The full
  list with descriptions mirrors upstream (52 labels).
- Black's input is only parsed, never executed. Formatting is checked with `--safe`
  (AST equivalence plus a second-pass stability check). This is the default.
- `INTERNAL ERROR: … different code on the second pass` = unstable formatting;
  `… produced invalid code` / `… not equivalent to the source` = crash-type bug;
  `Cannot parse` = parser error, or input invalid for the target version.
- Preview/unstable features (`--preview`, `--unstable`) are listed in
  `docs/the_black_code_style/future_style.md` and `src/black/mode.py` (`class Preview`).
- Python ≥ 3.9. Code style is Black itself (`black --check src/`).

## Agent workspace

The triage workflow checks out only `.claude/`, `.github/`, `docs/`, `src/` and the root files
(sparse checkout). A pre-agent step then deletes `analysis/`, `evals/` and `DESIGN.md`, failing
the job if any remains, so evaluation answers can never be read during triage. Ground-truth or
evaluation data must live only under `analysis/` or `evals/`.
The agent is Claude Code (gh-aw `claude` engine). It discovers the triage skill in
`.claude/skills/` and reads files with its Read/Grep tools (no edit or web tools).
The prefetch writes the trusted triage context to `.triage-context/` in the workspace (chmod
a-w; the agent has no Edit/Write grant there). The agent's only writable area is `/tmp`
(audit log, repro virtualenvs).

## Forbidden changes

- Do not modify anything under `src/`, `tests/`, `docs/`, `LICENSE`, or `AUTHORS.md`. They
  are the upstream snapshot and the attribution.
- Do not put evaluation answers or maintainer outcomes anywhere except `analysis/` or `evals/`,
  and do not widen the sparse checkout in `issue-triage.md` to include them.
- Do not edit `.github/workflows/*.lock.yml` by hand. Change the `.md` source and run
  `gh aw compile`.
- Do not widen `permissions`, `network`, `tools`, or `safe-outputs` in
  `.github/workflows/issue-triage.md`. `main` is protected (admins included): every change needs a
  PR with the `test` check green. After editing `issue-triage.md`, regenerate the red-team variant
  (`python3 evals/redteam/make_redteam_workflow.py`) and run `gh aw compile`.
- Do not add the upstream repository as a git remote. Do not open issues, PRs, or comments
  upstream, and do not mention upstream users or issue numbers in anything posted to GitHub.
