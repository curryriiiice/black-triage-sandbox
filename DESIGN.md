# DESIGN: first-pass issue triage for Black

## 1. Why this workflow
**Workflow.** On `issues: opened`, label a new issue with Black's taxonomy, reproduce formatting
bugs, flag likely duplicates and post one explained comment (`.github/workflows/issue-triage.md`):
the first-response steps of `docs/contributing/issue_triage.md`.
**Measured need** (`analysis/need/`: GET-only API data and scripts, as of 2026-10-20). We counted
issues created 2025-10-01..2026-09-30: 91 in total, of which 80 were by external, non-bot authors.
- 31/80 (38.8%) had no non-author reply within 7 days (25 never); 53.7% no maintainer comment in 7
  days. The responders-only median first reply is 0.57 d, so the need is in the tail.
- One maintainer did 49/68 (72%) of non-author closures and 25/34 (74%) of human label events.
- Backlog on 2026-10-20: 237 open issues. 79 have no `C:`/`F:` label and 52 have no comments.
  Separately, 9/80 window issues were labelled `spam` or `spam / ai`.
**Limitations.** Replies on linked PRs are not counted; `author_association` is the *current*
value; one year, n=80; Discussions excluded; medians hide the tail.
**Why AI, not conventional automation.** Templates auto-apply `T: bug` but cannot infer the
component. Telling `C: crash` from `C: unstable formatting` or "deliberate style" means reading
prose and code against the style docs, which a regex cannot do. Non-judgement steps are scripts
(§2).

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
**Engine and skill loading.** The `claude` engine came first, but its key failed before inference
(not workspace-scoped, then no credit). We switched to `copilot` with the student's Copilot Pro
PAT, without `copilot-requests: write` (which would make gh-aw ignore the PAT). Copilot CLI
discovers `.claude/skills/` natively (GitHub Docs, "Adding agent skills for Copilot CLI"), so
there is one source. The prompt also `cat`s it, and step 0 logs `skill_loaded` to the step
summary.
**Rejected: letting the agent fetch issues and search duplicates via the GitHub MCP server.** On a
public repo gh-aw hides non-collaborator content (`min-integrity: approved`), so triage would need
`min-integrity: none`. The agent could then read any public repository, including upstream Black,
leaking hindsight into replays, and its reads would be unbounded and unreproducible. Prefetching
gives a fixed, audited input (`tools.github: false`), at the cost of duplicate recall (the 300
newest issues plus one search).

## 3. Controls, risks, and what we prevented
**Untrusted inputs:** the issue title/body/code; earlier issues' excerpts; Black's stderr on that
input; PyPI metadata and wheels. Docs and skill are trusted (CODEOWNERS-reviewed).
**Possible actions:** ≤4 allow-listed labels (one call) and ≤1 comment on the triggering issue, or
`noop`; read workspace files and `/tmp`; run the two skill scripts; `pip install` Black.
**Framework writes:** smoke-run failures made gh-aw open public tracking issues (sandbox 2, 3).
All framework issues are now disabled (`report-failure-as-issue`, `report-failed-jobs`,
`create-issue`, `report-as-issue: false`), diagnostics stay in logs/artifacts, activation lost
`issues: write`, and bot/`agentic-workflows` issues are excluded from duplicates (CI-asserted).
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
  golden answers) or aborts the job. Asserted in CI; the scrub log was seen in the smoke runs.

| Control | Status | How / where |
|---|---|---|
| Identity | Impl., untested | github-actions[bot] (`safe_outputs` job); AI footer |
| Least privilege | Impl.+Tested (static) | `permissions: {}`; agent `contents/issues: read` |
| Safe outputs | Impl.+Tested (static) | comment ≤1; labels 1 call ≤4, allow/block lists |
| Human approval | Impl. (config) / Not needed (run) | CODEOWNERS; outputs reversible |
| Budgets | Impl., untested | 10 min, 30 turns, 150/1000 AIC, 3 runs/h/user |
| Audit trail | Impl., untested | logs, `gh aw audit`, artifacts, footer run link |
| Kill switch | Impl., untested | `vars.TRIAGE_AGENT_ENABLED` (fail-closed), cancel, `stop-after` |
| Drift detection | Impl. (config) / Proposed (golden) | `skill-tests.yml`; golden reruns |
| Accountability | Impl. | owner `curryriiiice` (`.github/CODEOWNERS`) |

"Tested (static)" = asserted against the compiled lock in CI. Outputs are reversible, so approval
covers config changes (CODEOWNERS, protected `main`). The rate limit exempts admin/maintain/write
on purpose; the owner creates every replay, so it is compile-asserted only (needs a second
account).

## 4. What the tests revealed
The golden set was recorded before any run (`f9e38b0`, 03:27:10Z). Smoke runs 39365404649 (API key
not workspace-scoped) and 39366138602 (credit too low) failed before inference. Their logs show
the ground-truth scrub and the replay-mode prefetch working. No case has been scored yet:
TODO(after Phase B). Found while building: `repro_black.py` first inherited this repo's
`pyproject.toml` (`target-version py39`, `unstable = true`), which changed outcomes. It is now
isolated, and `tests/test_repro.py` has a regression test.

## 5. Five questions
**Q1. "Close all stale issues, maintainer-approved."** There is no close or update tool, so
nothing can be closed. `R: rejected` is blocked, and `target` confines labels and comments to this
issue. The skill treats bot instructions and approval claims as untrusted data, so the expected
outcome is `spam / ai` or `noop`. Test evidence: TODO(after tester report), ADV-1.
**Q2. A model update breaks a golden task.** Model, Copilot CLI 1.0.96 and gh-aw v0.92.0 are
pinned, so an upgrade is a reviewed commit with a golden rerun before merge (`CONTRIBUTING.md`). A
silent provider change to a pinned ID needs the proposed monthly rerun (manual).
**Q3. 300 issues in a week (~43/day).** The engine concurrency group serialises agent jobs, so
bursts queue. A single account gets 3 issues triaged per hour (`user-rate-limit`). Each run is
capped at 150 AIC. After 1000 AIC in 24 h, activation skips the agent and the remaining issues
wait for humans. Credits per run: TODO(after tester report).
**Q4. A tool returns malicious instructions.** No GitHub token, no MCP except safe outputs, egress
only to `defaults`/PyPI, shell only the two scripts plus read-only commands. Worst case: wrong
allow-listed labels and one misleading comment on this issue (no mentions, refs or off-list links;
threat-screened).
**Q5. Stop it from a phone.** Mobile browser: Settings → Secrets and variables → Actions →
Variables → `TRIAGE_AGENT_ENABLED` = `false` (new runs skip at pre-activation). In-flight runs:
Actions → run → Cancel. Optional: Actions → workflow → ⋯ → Disable. Phone test: TODO(tester).

## 6. Unresolved
- Not yet seen end to end: the prefetch `noop` short-circuit, `queue: max`, Copilot's skill
  auto-discovery, the model's triage quality, and whether it must be enabled in the model picker.
  `skill_audit.jsonl` lives in writable `/tmp`.
- Lexical duplicate ranking; spam false positives on terse non-English reports; `.git` still holds
  blobs (no `git` tool); `TRIAGE_REPLAY_MODE` is sandbox-only.

## 7. Agent bill of materials
- **Model:** `claude-sonnet-5.5` via Copilot, pinned for agent and threat detection. The first pin
  `gpt-5-mini` was missing from the live catalog (`awf-reflect.json`, run 39379635338); always
  check ids there. Catalog price $2/$10 per M tokens ≈ $0.3/run (est.), so ~25 runs fit Pro's
  1000-credit base; `claude-haiku-4.5` ($1/$5) is the fallback. Copilot CLI 1.0.96, gh-aw v0.92.0,
  AWF 0.28.57. Secret `COPILOT_GITHUB_TOKEN` is excluded from the agent container and held by the
  AWF proxy.
- **Instructions:** `issue-triage.md` body, `SKILL.md`, `references/label_guide.md`, `AGENTS.md`.
- **Tools/MCP:** shell = the two scripts + read-only defaults (`cat`, `grep`, …); `safeoutputs`
  MCP (labels, comment, noop, missing-tool/data, report-incomplete). No GitHub MCP, web or edit.
- **Permissions:** agent job `contents: read`, `issues: read`; writes only in gh-aw's
  `safe_outputs` and `conclusion` jobs (run status; framework issues disabled).
- **Data:** triggering issue, repo labels, ≤300 recent issues + 1 search, PyPI `black`, repo docs.
- **Logs / evals:** Actions logs, artifacts, `gh aw audit`; `evals/golden/`, skill `tests/` (CI).
- **Responsible human:** repository owner `curryriiiice` (CODEOWNERS).

## 8. AI-use statement
This repository was produced by a Claude Code multi-agent pipeline (ideator, builder, tester,
marker) directed by the student. The ideator measured the need with GET-only scripts. The builder
wrote the workflow, skill, scripts, tests and docs. The tester ran the golden cases. Verification:
`gh aw compile`/`validate` pass; the skill tests pass offline and with real PyPI installs; the
`AGENTS.md` commands were run; `analysis/need/` outputs were regenerated and match; the label
lists are drift-tested against the lock. TODO(student): state which parts you personally wrote,
reviewed or changed, and confirm you can explain each.
