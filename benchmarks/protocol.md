# Fixed exploratory benchmark protocol

Protocol date: November 11, 2026. Freeze this file, the suite, runner and prompts before scored runs. The manifest records their hashes and Git revision. Infrastructure capability probes use no suite task and are excluded.

## Question and scope

Compare a normal single coding-agent session with one bounded Daisychain round on the same four synthetic Python repair tasks, repeated three times: 12 paired attempts and 24 workflow runs. This is a natural-workflow comparison with measured compute, not an equal-token-budget experiment.

Both arms use GPT-6.1 Sol (`gpt-6.1-sol`), low reasoning, Standard/default service, Codex CLI, Python 3.12, identical task requirements, starting source and public tests. No model seed is exposed. Three repetitions are new sessions, not best-of-three selection. The model identifier is an alias and may drift in a future replication.

Capability probes found slow model-catalog refresh requests in this local environment. Before scored runs, the runner snapshots the local CLI model catalog and supplies that same snapshot to every session using model_catalog_json. The manifest records its hash. This removes catalog refresh timeouts from the comparison and pins local model metadata; it does not pin server model weights. The private catalog is not published.

## Conditions

- **Single:** one fresh session may diagnose, plan, edit, run public/custom tests, inspect failures and self-review. It may revise within its session.
- **Daisychain:** four fresh sessions: grader, strategist, implementer, regrader. The grader sees the original artifact without proposed fixes. The strategist receives the grader handoff. The implementer receives both handoffs and may self-review and revise within its session. The regrader sees the final artifact and criteria first, then a baseline diff, without previous grades, plan or implementation rationale. It is read-only. There is one implementation round and no second repair after regrading.

Each workflow has a 480-second ceiling, including model/tool execution, process startup and handoff construction. Workspace preparation and final external scoring are excluded. The same ceiling is not a matched inference budget. The chain's additional context and calls are part of its measured overhead. Task-solving workflows run serially, in adjacent randomized pairs with balanced first-arm order and schedule seed 20261111.

Each session receives local shell/Python tools; writing is enabled only for the baseline and implementer. Both may edit only solution.py. Network, other workspaces, hidden evaluation code, external records and recursive subagents are disallowed. Host skills, user config, project instructions, memories, hooks and plugins are disabled in the controlled calls. CLI sandbox controls writes; withheld files are outside the candidate workspace and not supplied in prompts, rather than claimed to be inaccessible to all reads. Published command traces support auditing task-related tool use.

The full SKILL.md instructions are embedded in the chain prompts. Optional linked templates/references are not materialized in scratch workspaces. This measures that fixed embedded-instruction configuration, not installation or automatic discovery of the complete skill package.

## Quality and failures

The suite and evaluator are fixed before runs. Held-out checks exercise stated requirements and regressions, never extra undocumented requirements. All candidates are frozen before any held-out scoring. The deterministic evaluator is the same for both conditions; there is no subjective LLM judge.

Primary quality: fraction of attempts completing their workflow and passing every held-out check and public smoke test. Secondary: mean held-out check-pass fraction per task attempt, weighted equally across tasks. Public smoke results are recorded separately from the 60 held-out checks. Report all checks and any deviations. A complete solution from an incomplete workflow is still an unsuccessful workflow in the primary metric; report evaluator quality separately.

Include scheduled failures, timeouts, malformed outputs and scope violations. There are no automatic scored retries or cherry-picked replacements. Infrastructure failures remain visible. Stop the run if repeated authentication or service failures make further measurement meaningless; publish the partial result and reason rather than inventing complete data. Never alter a task after seeing scored outputs without declaring a new benchmark version.

## Speed and cost

Use a monotonic clock for total workflow latency; exclude final held-out evaluation. Report mean, median and paired differences/ratios where defined. Do not run scored workflows concurrently.

Extract usage from Codex JSONL `turn.completed.usage`: input_tokens, cached_input_tokens and output_tokens. Cached input is a subset of input. Sum completed-stage usage; output already includes billed reasoning output, so do not add a reasoning subset again. Missing usage remains unknown, not zero. Store completion/coverage flags and mark partial-cost totals as lower bounds.

Estimate Standard Codex credits using the dated official GPT-6.1 Sol rate card: `(uncached_input * 50 + cached_input * 2.5 + output * 250) / 1_000_000`. Source: [Codex pricing](https://learn.chatgpt.com/docs/pricing#token-rates), checked November 11, 2026. This token-based estimate is not observed subscription consumption, purchased credits, or a dollar invoice. No claim of zero cost follows from using subscription authentication.

## Interpretation and publication

Publish the manifest/schedule, exact prompts, sanitized handoffs and tool-event summaries, final code/diffs, per-check results, raw usage and aggregation code. Keep authentication state, full private CLI logs and machine-specific paths out of Git. Record operator intervention and deviations. This run requires no manual correction of candidate answers.

Results are descriptive for four task families and one configuration. Repeated runs are nested within tasks, not 12 independent task types. Report ties and ceiling effects. Do not generalize to UI usability, production changes, other models or all multi-agent systems. A future equal-budget study and more difficult independently sourced tasks are separate experiments.
