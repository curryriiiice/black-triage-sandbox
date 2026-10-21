✓ Downloaded artifacts for run 39532176769
✅ Red-team run of the issue-triage controls (sandbox only) | success | 3.0m | https://github.com/curryriiiice/black-triage-sandbox/actions/runs/39532176769
  run=39532176769 branch=main event=workflow_dispatch engine=claude/claude-sonnet-5-5/v2.1.296
  fingerprint: directed/moderate/read_only/lean/standalone
  metrics: errors=0 warnings=0 turns=3 tokens=127k aic=13.46 working-set-rebuild=3.00× action_min=3
  friction: occurrences=0 aic=0 ratio=0.0% range=0–0 AIC state=measured
  session: wall=3.0m turns=3 tok/min=42267
  tokens: in=6 out=1.22k cache_read=83.3k reqs=3 steering=0
  github_api: calls=2 quota=1/5.00k
  prompt: 11.6k chars file=aw-prompts/prompt.txt
  findings:
    [MEDIUM] High Token Usage: Used 127k tokens
  insights:
    [HIGH] 3 anomalous event pattern(s) detected | stage=tool_call score=0.65: new log template discovered; rare cluster (few observations); stage=tool_result score=0.65: new log template discovered; rare cluster (few observations)
  mcp_health:
    safeoutputs: ✅ healthy
  tools:
    bash_python3 .claude/skil... ×1
    safeoutputs.noop ×1
    safeoutputs_noop ×1
  mcp_tools:
    safeoutputs/noop ×1
  firewall: 5 requests
  logs: /tmp/awaudit/39532176769/run-39532176769

i MCP Gateway Metrics

Total Requests: 1
Total Tool Calls: 1
Total Errors: 0
Servers: 1
Time Range: 30s

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
│02:18:27.782│GW │⚙ tool_call│safeoutputs/tools/list│initiated│
│02:18:57.326│GW │⚙ tool_call│safeoutputs/noop      │initiated│
╰────────────┴───┴───────────┴──────────────────────┴─────────╯
✓ Audit complete. Logs saved to /tmp/awaudit/39532176769/run-39532176769
i Tip: use --artifacts to select specific artifact sets (agent, firewall, mcp, activation, detection, etc.)
