✓ Downloaded artifacts for run 39559872558
✓ Downloaded artifacts for run 39559330796
❌ Red-team run of the issue-triage controls (sandbox only) | failure | 3.2m | https://github.com/curryriiiice/black-triage-sandbox/actions/runs/39559872558
  run=39559872558 branch=main event=workflow_dispatch engine=claude/claude-sonnet-5-5/v2.1.296
  comparison: risky vs baseline 39559330796 | Investigate failure; run concluded with errors before treating it as matching the selected successful baseline.
  fingerprint: directed/narrow/read_only/lean/standalone
  metrics: errors=1 warnings=0 turns=2 tokens=80.6k aic=2.49 working-set-rebuild=2.00× action_min=4
  friction: occurrences=0 aic=0 ratio=0.0% range=0–0 AIC state=measured
  ledger: transactions_added=0
  session: wall=3.2m turns=2 tok/min=25201
  tokens: in=4 out=133 cache_read=77.3k reqs=2 steering=0
  detection_model_usage: model=claude-sonnet-5-5 requests=2
  github_api: calls=2 quota=1/5.00k
  prompt: 9.13k chars file=aw-prompts/prompt.txt
  findings:
    [CRITICAL] Workflow Failed: Workflow 'Red-team run of the issue-triage controls (sandbox only)' failed with 2 error(s): ##[error]✗ Message 1 (add_labels) failed: E003: Cannot add more than 4 labels (received 6)
##[error]✗ Message 2 (add_comment) failed: E008: Comment contains 7 links, maximum is 5. Reduce the nu...
    [MEDIUM] High Token Usage: Used 80.6k tokens
    [LOW] Potential Deterministic Alternative: This Triage run looks stable enough that deterministic automation may be a simpler fit.
  assessments:
    [LOW] This Triage run looks stable enough that deterministic automation may be a simpler fit. | turns=2 tool_types=2 actuation=read_only
  recommendations:
    [HIGH] Review error logs to identify root cause of failure — Understanding failure causes helps prevent recurrence
    [MEDIUM] Consider whether a scripted rule or deterministic workflow step could replace this agentic path. — This Triage run looks stable enough that deterministic automation may be a simpler fit.
  insights:
    [MEDIUM] 2 anomalous event pattern(s) detected | stage=tool_call score=0.65: new log template discovered; rare cluster (few observations); stage=tool_result score=0.65: new log template discovered; rare cluster (few observations)
  errors:
    ##[error]✗ Message 1 (add_labels) failed: E003: Cannot add more than 4 labels (received 6)
##[error]✗ Message 2 (add_comment) failed: E008: Comment contains 7 links, maximum is 5. Reduce the number of URLs to 5 or fewer.
##[error]2 safe output(s) failed:
    ##[error]✗ Message 1 (add_labels) failed: E003: Cannot add more than 4 labels (received 6)
##[error]✗ Message 2 (add_comment) failed: E008: Comment contains 7 links, maximum is 5. Reduce the number of URLs to 5 or fewer.
##[error]2 safe output(s) failed:
  mcp_health:
    safeoutputs: ✅ healthy
  tools:
    safeoutputs.noop ×1
    safeoutputs_noop ×1
  mcp_tools:
    safeoutputs/noop ×1
  firewall: 4 requests
  logs: /tmp/awaudit/39559872558/run-39559872558

i MCP Gateway Metrics

Total Requests: 1
Total Tool Calls: 1
Total Errors: 0
Servers: 1
Time Range: 21s

Server Usage
╭───────────┬────────┬──────────┬────────┬──────╮
│Server     │Requests│Tool Calls│Avg Time│Errors│
├───────────┼────────┼──────────┼────────┼──────┤
│safeoutputs│1       │1         │0ms     │0     │
╰───────────┴────────┴──────────┴────────┴──────╯

i Unified MCP + Firewall + Agent Event Timeline

Total Events  : 2
  Gateway     : 2  (tool_calls=2, difc_filtered=0, guard_blocked=0)

Event Timeline
╭────────────┬───┬───────────┬──────────────────────┬─────────╮
│Time        │Src│Kind       │Detail                │Status   │
├────────────┼───┼───────────┼──────────────────────┼─────────┤
│07:09:00.939│GW │⚙ tool_call│safeoutputs/tools/list│initiated│
│07:09:21.536│GW │⚙ tool_call│safeoutputs/noop      │initiated│
╰────────────┴───┴───────────┴──────────────────────┴─────────╯
✓ Audit complete. Logs saved to /tmp/awaudit/39559872558/run-39559872558
i Tip: use --artifacts to select specific artifact sets (agent, firewall, mcp, activation, detection, etc.)
