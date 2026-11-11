# Daisychain

**A reusable agent workflow for reviewing, improving, and checking work.**

```text
Objective → Grade → Propose → Implement → Regrade → Stop or repeat
```

Daisychain gives each pass a clear job, concrete evidence, and a handoff to the next pass. Use it for product usability, code, documentation, or strategy when a separate review can catch mistakes the implementer misses.

This repository contains an instruction-based agent skill and reusable templates. Your host supplies models, tools, subagents, permissions, and execution. There is no bundled orchestration service or autonomous runtime.

## Quick start

Read [SKILL.md](SKILL.md), then give your agent a bounded request:

> Use $daisychain to improve this app's onboarding. First grade the current flow, propose the smallest useful changes, implement them, then independently regrade against the original requirements. Verify the empty, error, and success states. Limit the run to two improvement rounds.

For a review-only request:

> Use $daisychain to review this document and recommend changes. Stop before implementation.

Use the [run brief](templates/brief.md) to capture the objective, acceptance criteria, allowed actions, and effort budget. The [handoff](templates/handoff.md) and [report](templates/report.md) keep the evidence intact across passes. See a [synthetic UI example](examples/ui-audit.md).

## Install as a local skill

For a personal Codex skill, clone into the documented user skill directory:

```bash
mkdir -p "$HOME/.agents/skills"
git clone https://github.com/samthedataman/daisychain.git "$HOME/.agents/skills/daisychain"
```

Git refuses to clone into an existing nonempty directory. If you already have a skill named `daisychain`, review the versions and choose one deliberately; duplicate names can both appear in skill selectors. Codex normally detects changes automatically; restart it if the skill does not appear. See the [official skills documentation](https://learn.chatgpt.com/docs/build-skills).

For a project-scoped skill, clone into `.agents/skills/daisychain` inside the target project instead. Other agent hosts can use the Markdown instructions and templates, but their discovery, delegation, and permission behavior must be configured separately. Cross-host execution has not been tested here.

## The four roles

| Role | Responsibility | Output |
| --- | --- | --- |
| Grader | Inspect the current artifact against the objective | Evidence, weaknesses, baseline assessment |
| Strategist | Choose a small, high-impact improvement | Bounded plan, target artifacts, expected effect |
| Implementer | Apply the selected changes | Diff or revised artifact, relevant check results |
| Regrader | Inspect the result against the same criteria | Before/after evidence, regressions, stop or loop decision |

These are logical roles. Use separate agents when the host allows delegation and the added review is useful. If one agent performs the roles sequentially, disclose that the review was not independent. Multiple agents using the same model can still share the same mistakes.

## Why this resembles modern agent systems

Modern systems document related patterns: Anthropic's prompt chains and evaluator-optimizer loops, LangGraph's conditional workflows, and OpenAI's orchestration primitives. Anthropic also describes a planner, generator, and evaluator harness with structured handoffs and explicit criteria. These are independent examples of the broader approach; there is no evidence that these systems adopted this repository or its name.

See [the sourced comparison](docs/research.md) for the details and limits of each connection.

## What team research suggests

Human team studies motivate several design choices: write down the shared goal, collect judgments before showing proposed answers, preserve unusual or conflicting evidence, make uncertainty easy to report, and finish with a structured review. These are design hypotheses for agent workflows. Human findings do not establish that the same intervention improves LLM performance.

The public skill makes these choices concrete:

- Define acceptance criteria before implementation; keep subjective grades separate from verified checks.
- Give reviewers the raw artifact and criteria before the implementer's rationale where practical.
- Carry counterevidence and unresolved disagreements into the final decision.
- Set an effort budget and a maximum number of rounds.
- Compare outcomes with a simpler single-agent baseline before claiming an improvement.

## First benchmark: November 11, 2026

The [published pilot](benchmarks/results/2026-11-11-pilot/RESULTS.md) compares four synthetic Python repair tasks, each repeated three times in both conditions: 12 paired attempts, 24 workflows, and 60 CLI sessions. Both arms use GPT-6.1 Sol with low reasoning, the same starting files, requirements and tools. The protocol was [published before scored execution](https://github.com/samthedataman/daisychain/commit/870a091f78539703e8ec160eb8e0b2ec607393ff).

| Metric | Single agent | Daisychain, one round |
| --- | ---: | ---: |
| Attempts completing and passing all checks | 12/12 | 12/12 |
| Mean workflow time | 52.62 s | 206.38 s |
| Median workflow time | 50.35 s | 183.68 s |
| Mean estimated Standard Codex credits | 1.1120 | 3.6416 |
| Mean API-equivalent estimate in USD | $0.0445 | $0.1457 |

Functional quality reached a ceiling on these tasks. The chain took 3.92 times as long and used 3.27 times the estimated credits, using ratios of the overall means, without improving the measured pass rate. One chain included a 356-second planning stage and completed just inside the 480-second limit; it remains in the results. A full-quality tie does not establish equivalence on harder tasks.

Credit estimates use the [dated Codex rate card](https://learn.chatgpt.com/docs/pricing#token-rates). The optional USD conversion uses [Standard API prices](https://developers.openai.com/api/docs/pricing), checked November 11, 2026: $2 uncached input, $0.10 cached input, and $10 output per million tokens. All observed cache-write counts were zero and context sizes fit the short-context rates. Actual subscription consumption and dollar billing were not observed. This is a natural-workflow comparison, not equal inference compute.

Read the [full report](benchmarks/results/2026-11-11-pilot/RESULTS.md), [run notes](benchmarks/results/2026-11-11-pilot/RUN_NOTES.md), [integrity audit](benchmarks/results/2026-11-11-pilot/audit.json), and [reproduction instructions](benchmarks/README.md). The repository includes exact prompts, sanitized handoffs and command summaries, solutions, per-check results, usage and aggregation code.

## Evidence and current limits

The pilot measures one fixed configuration on four small synthetic task families. It does not establish broad agent, production-engineering or usability benefits. The separate worked UI example remains fictional. Agent-assigned grades are not benchmark quality scores.

The [evaluation plan](docs/evaluation.md) describes the next comparisons needed. Contributions with reproducible, sanitized evidence are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE).
