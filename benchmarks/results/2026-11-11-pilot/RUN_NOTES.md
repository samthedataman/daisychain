# Run notes and limits

The protocol, task suite and generation runner were published in commit `870a091` before scored execution began. The manifest records that source revision, file hashes and the frozen randomized schedule. Capability probes and benchmark-development work are excluded from workflow timing and token totals.

## Configuration measured

This is an embedded-instruction, one-round Daisychain configuration: grade, propose, implement, then read-only regrade. The final reviewer can identify a remaining defect but cannot trigger another repair. The comparison does not measure every configuration allowed by the skill, an installed plugin, or an adaptive multi-round loop.

The single agent can plan, test and revise within its session. The implementer can do the same within its stage. Both receive the same requirements, starting source and public tests. All held-out evaluations occur after every candidate is frozen; no held-out feedback is sent to measured agents.

Each workflow has the same wall-time ceiling, while the chain gets four fresh sessions. This is not equal inference compute. Workflow token totals include the repeated context and reviews. The experiment measures four synthetic task families on one model/settings combination; repeated attempts are not independent task types.

The local Codex CLI uses a private snapshot of its model catalog to avoid model-discovery refresh timeouts found during capability probes. The manifest records the snapshot hash. It pins local metadata, not server weights. Requested model, reasoning and service settings are recorded by the runner; the CLI events do not independently attest an immutable server-side model snapshot. Private model catalogs and authentication state are excluded from publication.

Candidate workspaces are temporary directories without Git repositories. Task code, local shell/Python checks and final diffs are available, but an agent's attempted `git diff` can fail there. Such commands and their time/token overhead are retained; they are not grounds for excluding a run. This environment differs from a production repository checkout.

## What is and is not measured

- Primary quality requires workflow completion plus all fixed held-out checks and public smoke tests. Secondary check-pass fractions use the held-out checks only. Passing these checks is not a proof of correctness for all inputs.
- Time includes the workflow's CLI startup, model responses, local tools and handoffs. It excludes initial workspace setup and external final scoring. Provider latency and other host activity are not controlled as in a laboratory timing experiment.
- Cost is a token-based estimate in Standard Codex credits using the dated official rate card. Actual subscription consumption and dollar billing are not observed. Preparation, capability probes, benchmark development and operator coordination are outside the per-workflow comparison.
- Fields named `tool_calls` in frozen telemetry count completed shell-command execution items only. Public trace files contain usage events and selected command summaries; they omit file-change and other tool-event types. They provide a limited command audit, rather than proof of all tool behavior. Final source/diffs and protected-file checks provide separate, limited artifact checks.
- Withheld evaluator code is outside the candidate workspace and not supplied to agents. The host does not enforce that all filesystem reads are restricted to the workspace. The bounded evaluator subprocess is not a security sandbox for hostile submissions.

No agent-assigned grade is used as a quality score. Interpret any full-quality tie as a ceiling on these tasks, not evidence that the approaches are equivalent on harder work. A budget-matched study, independently sourced tasks, additional models, and an adaptive repair loop would be separate experiments.

## Observed outcome and integrity

All 24 scheduled workflows completed, with 60 completed stage calls and complete usage records. The 360 held-out checks and 48 public smoke tests passed. The [integrity audit](audit.json) confirms frozen source hashes, final solution hashes, stage-to-event usage, workflow-to-stage usage sums, schedule identities, and the private catalog snapshot hash.

One strategist stage in `21-query_patch-r2-daisychain` took 356.17 seconds; that workflow completed at 478.40 seconds within the 480-second limit. Its exported events report no error, and inspection of its private stderr found no catalog-refresh timeout, connection-retry or rate-limit messages. The cause of the delay is not established. The run was not retried or excluded. Mean and median times are both reported.

The two conditions both passed every check, so this pilot measures an efficiency difference at a functional-quality ceiling. The workflow totals are 631.40 seconds and 13.34447 estimated credits for the single-agent arm, versus 2,476.61 seconds and 43.69976 estimated credits for Daisychain. These totals cover task-solving workflows only.

For an optional dollar comparison, [Standard API prices](https://developers.openai.com/api/docs/pricing), checked November 11, 2026, are $2 uncached input, $0.10 cached input and $10 output per million tokens for this model's short-context tier. Every stage's aggregate input count is below 272,000 tokens, and cache-write counts are zero. Under those assumptions the API-equivalent estimate is `credits × $0.04`: $0.04448 per single-agent attempt and $0.14567 per Daisychain attempt. This conversion is informational, not a preregistered outcome or an observed invoice.
