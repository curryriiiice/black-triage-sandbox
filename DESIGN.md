# DESIGN: first-pass issue triage for Black

## 1. Why this workflow
**Workflow.** On `issues: opened`, label a new Black issue with Black's own taxonomy, reproduce
formatting bugs, flag likely duplicates, and post one explained comment
(`.github/workflows/issue-triage.md`). These are the first-response steps of Black's triage guide
(`docs/contributing/issue_triage.md`).
**Measured need** (`analysis/need/`: GET-only API data and scripts, as of 2026-10-20). We counted
issues created 2025-10-01..2026-09-30: 91 in total, of which 80 were by external, non-bot authors.
- 31/80 (38.8%) got no reply from anyone but the author within 7 days, and 25 never got one. 53.7%
  had no maintainer comment within 7 days. Among issues that got a reply, the median first reply
  was 0.57 d, so the need is in the tail.
- One maintainer did 49/68 (72%) of non-author closures and 25/34 (74%) of human label events.
- Backlog on 2026-10-20: 237 open issues. 79 have no `C:`/`F:` label and 52 have no comments.
  Separately, 9/80 window issues were labelled `spam` or `spam / ai`.
**Limitations.** Replies on linked PRs are not counted, so some "silent" closures were answered
elsewhere. `author_association` is the *current* value. There is one year of data and n=80.
Discussions are excluded. Medians hide the tail.
**Why AI, not conventional automation.** The issue templates already auto-apply `T: bug`, which is
the conventional baseline, but they cannot infer the component. Telling `C: crash` from `C:
unstable formatting` or "deliberate style" means reading prose and code against the style docs,
which a regex cannot do. Every step that needs no judgement is a script (section 2).

## 2. Design and rejected alternative
Facts are in `AGENTS.md`, the procedure is in `.claude/skills/black-issue-triage/SKILL.md`, and
hard limits are in the workflow frontmatter. The skill's scripts do the non-judgement work:
- `prefetch_context.py` is a `pre-agent-steps` step that uses the read-only token. It skips
  maintainer, bot and already-triaged issues by writing a `noop`, so no inference cost is
  incurred. It extracts fenced blocks and Python-looking inline code, lists the Black releases
  that existed on the issue's date, and ranks earlier issues as duplicate candidates.
- `repro_black.py` installs the *reported* release (wheels only), ignores any `pyproject.toml`,
  and formats twice to check stability. It never executes the snippet.
- `validate_labels.py` checks the proposed labels against the policy, the repo labels and the
  repro evidence before the agent emits them.
**Rejected: letting the agent fetch issues and search duplicates via the GitHub MCP server.** On a
public repo gh-aw hides non-collaborator content (`min-integrity: approved`), so triage would need
`min-integrity: none`. The agent could then read any public repository, including upstream Black,
leaking hindsight into replays, and its reads would be unbounded and unreproducible. Prefetching
gives a fixed, audited input (`tools.github: false`), at the cost of duplicate recall (the 300
newest issues plus one search). First-pass *PR* review was rejected too: heavy context, noisier
output.

## 3. Controls, risks, and what we prevented
**Untrusted inputs:** the issue title/body/code; earlier issues' excerpts; Black's stderr on that
input; PyPI metadata and wheels. Docs and skill are trusted (CODEOWNERS-reviewed).
**Possible actions:** ≤4 allow-listed labels (one call) and ≤1 comment on the triggering issue, or
`noop`; read workspace files and `/tmp`; run the two skill scripts; `pip install` Black.
**Deliberately prevented** by configuration, not by prompt:
- Closing, locking, editing, assigning or deleting. No such safe output exists, and
  `tests/test_config_consistency.py` asserts that none is compiled into the lock.
- Decision labels (`R: not a bug`, `R: rejected`, `S: accepted`, `help wanted`, …). These are in
  `add-labels.blocked`, so the agent can only suggest them.
- Touching other issues: `target` is pinned to the triggering or dispatched number.
- Pings and cross-references (`mentions: false`, `allowed-github-references: [repo]`). Links are
  capped at 5 and must be on allow-listed domains.
- Executing reporter code, using Black releases newer than the issue, web or GitHub API access,
  and repository edits (`tools.edit: false`). Egress is limited to `defaults` and `python`.
- Triaging maintainers' own issues, or the same issue twice (prefetch skip rules).
- Reading ground truth: `checkout.sparse-checkout` holds only `.claude/ .github/ docs/ src/`, and
  a fail-closed pre-agent step deletes `analysis/`, `evals/` and `DESIGN.md` (maintainer outcomes,
  golden answers) or aborts the job. Asserted and executed against the lock in CI.

| Control | Status | How / where |
|---|---|---|
| Identity | Impl., untested | github-actions[bot] (`safe_outputs` job); AI footer |
| Least privilege | Impl.+Tested (static) | `permissions: {}`; agent `contents/issues: read` |
| Safe outputs | Impl.+Tested (static) | comment ≤1; labels 1 call ≤4, allow/block lists |
| Human approval | Impl. (config) / Not needed (run) | CODEOWNERS; outputs reversible |
| Budgets | Impl., untested | 10 min, 30 turns, 150/1500 AIC, 3 runs/h/user |
| Audit trail | Impl., untested | logs, `gh aw audit`, artifacts, footer run link |
| Kill switch | Impl., untested | `vars.TRIAGE_AGENT_ENABLED` (fail-closed), cancel, `stop-after` |
| Drift detection | Impl. (config) / Proposed (golden) | `skill-tests.yml`; golden reruns |
| Accountability | Impl. | owner `curryriiiice` (`.github/CODEOWNERS`) |

"Tested (static)" means `test_config_consistency.py` asserts it against the compiled lock in CI.
Per-run approval would defeat the speed goal, and every output is reversible, so approval applies
to configuration changes instead (CODEOWNERS plus branch protection on `main`). The owner reviews
golden reruns by comparing labels and comments with the expected outcomes. The rate limit exempts
admin/maintain/write on purpose, so re-dispatching maintainers are never throttled. The owner
creates every sandbox replay, so `ignored-roles: []` would throttle the evaluation itself. It is
compile-asserted only; exercising it needs a second, non-collaborator account.

## 4. What the tests revealed
TODO(after tester report, round 1): pass/fail summary of `evals/golden/`, every failure with its
cause, and the adversarial result. Found while building: `repro_black.py` first inherited this
repo's `pyproject.toml` (`target-version py39`, `unstable = true`), which changed outcomes. It is
now isolated, and `tests/test_repro.py` has a regression test.

## 5. Five questions
**Q1. "Close all stale issues, maintainer-approved."** There is no close or update tool, so
nothing can be closed. `R: rejected` is blocked, and `target` confines labels and comments to this
issue. The skill treats bot instructions and approval claims as untrusted data, so the expected
outcome is `spam / ai` or `noop`. Test evidence: TODO(after tester report), ADV-1.
**Q2. A model update breaks a golden task.** Model `claude-sonnet-5-5`, Claude Code 2.1.296 and
gh-aw v0.92.0 are pinned (lock metadata), so an upgrade is a reviewed commit that runs
`skill-tests`. `CONTRIBUTING.md` requires a golden rerun before merge, which is where the failure
shows. A silent provider-side change to a pinned ID is only caught by the proposed monthly rerun
(not automated).
**Q3. 300 issues in a week (~43/day).** The engine concurrency group serialises agent jobs, so
bursts queue. A single account gets 3 issues triaged per hour (`user-rate-limit`). Each run is
capped at 150 AIC. After 1500 AIC in 24 h, activation skips the agent and opens a guardrail issue,
and the remaining issues wait for humans. Credits per run: TODO(after tester report).
**Q4. A tool returns malicious instructions.** No GitHub token, no MCP except safe outputs, egress
only to `defaults`/PyPI, Bash only the two scripts. Worst case: wrong allow-listed labels and one
misleading comment on this issue (no mentions, refs or off-list links; threat-screened).
**Q5. Stop it from a phone.** Mobile browser: Settings → Secrets and variables → Actions →
Variables → `TRIAGE_AGENT_ENABLED` = `false` (new runs skip at pre-activation). In-flight runs:
Actions → run → Cancel. Optional: Actions → workflow → ⋯ → Disable. Phone test: TODO(tester).

## 6. Unresolved
- Not yet seen end to end: the prefetch `noop` short-circuit, `queue: max` under bursts, and
  skill auto-discovery (the prompt also names the skill).
- The agent may edit `/tmp` (gh-aw default), so `skill_audit.jsonl` is tamper-able; the transcript
  artifact is authoritative.
- Duplicate ranking is lexical; spam detection may flag terse non-English reports;
  `TRIAGE_REPLAY_MODE` is for the sandbox evaluation only and must stay unset in production.
- The `.git` pack in the agent workspace still holds all blobs. The agent has no `git` command and
  cannot decompress the objects with Read/Grep.

## 7. Agent bill of materials
- **Model:** `claude-sonnet-5-5` (Anthropic API), pinned. It also runs threat detection. The
  harness is Claude Code CLI 2.1.296 (compiler-pinned), gh-aw v0.92.0 and AWF 0.28.57.
- **Instructions:** `issue-triage.md` body, `SKILL.md`, `references/label_guide.md`, `AGENTS.md`.
- **Tools/MCP:** Read/Grep/Glob/LS; Bash = the two scripts + read-only defaults; `safeoutputs` MCP
  (`add_labels`, `add_comment`, `noop`, missing-tool/data, report-incomplete). No GitHub MCP/web.
- **Permissions:** the agent job has `contents: read` and `issues: read`. Writes happen only in
  gh-aw's `safe_outputs`, `activation` and `conclusion` jobs.
- **Data:** triggering issue, repo labels, ≤300 recent issues + 1 search, PyPI `black`, repo docs.
- **Logs / evals:** Actions logs, `agent`/`triage-audit` artifacts, `gh aw audit`; `evals/golden/`,
  skill `tests/` (CI). **Responsible human:** repository owner `curryriiiice` (CODEOWNERS).

## 8. AI-use statement
This repository was produced by a Claude Code multi-agent pipeline (ideator, builder, tester,
marker) directed by the student. The ideator measured the need with GET-only scripts. The builder
wrote the workflow, skill, scripts, tests and docs. The tester ran the golden cases. Verification:
`gh aw compile`/`validate` pass; the skill tests pass offline and with real PyPI installs; the
`AGENTS.md` commands were run; `analysis/need/` outputs were regenerated and match; the label
lists are drift-tested against the lock. TODO(student): state which parts you personally wrote,
reviewed or changed, and confirm you can explain each.
