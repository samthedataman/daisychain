# Agent systems and human-team research

Sources checked November 10, 2026. This note distinguishes documented agent patterns, findings about human teams, and proposed implications for Daisychain. Similarity does not establish that any system adopted this repository or the name Daisychain.

## Related patterns in modern agent systems

### Anthropic: composable workflows

[Building effective agents](https://www.anthropic.com/research/building-effective-agents), December 19, 2024, describes prompt chaining, orchestrator-workers, and evaluator-optimizer workflows. Chains pass one step's output to the next; intermediate checks can gate progress. Evaluator-optimizer workflows use feedback to guide another attempt.

Daisychain combines these established ideas: role-specific passes, concrete handoffs, and a conditional improvement loop. The article supports using composable patterns when they help; it does not validate this skill's effectiveness.

### Anthropic: planner, generator, evaluator

[Harness design for long-running application development](https://www.anthropic.com/research/harness-design-long-running-apps), March 24, 2026, describes a planner, generator, and evaluator with structured handoffs and explicit evaluation criteria. It discusses generous self-evaluation and the need to calibrate a separate evaluator as well.

This is a close documented parallel to planning, implementation, and regrading. It supports testing role separation as a design choice, while showing why an evaluator's approval alone is insufficient.

### LangGraph: explicit state and transitions

[Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) provides implementations of chaining, orchestrator-worker patterns, and evaluator-optimizer loops. Structured feedback and conditional routing determine whether work is repeated or completed.

A future Daisychain adapter could encode its brief, handoffs, and stop decisions as graph state. The current repository supplies instructions and templates; it does not implement a LangGraph integration.

### OpenAI: orchestration primitives

[Official OpenAI documentation: Building agents — orchestration](https://developers.openai.com/tracks/building-agents#orchestration) describes agent orchestration and SDK primitives including agents, handoffs, guardrails, sessions, and tracing. These enable specialized roles and observable transfers of work.

The primitives can support a Daisychain-style process. They do not automatically enforce independent grading, calibrated criteria, or the exact four-role sequence. See [official skill documentation](https://learn.chatgpt.com/docs/build-skills) for the instruction-package format used by this repository.

### Failure and cost evidence

[Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) examines more than 1,600 annotated traces across seven frameworks. Its taxonomy includes system-design problems, inter-agent misalignment, and task verification failures. This motivates explicit contracts and checks; it does not establish that Daisychain fixes these failures.

[Anthropic's multi-agent research-system report](https://www.anthropic.com/research/multi-agent-research-system) describes substantial token overhead and difficulties with tightly coupled tasks. Its approximately 15-times-chat token observation belongs to that system and comparison. It is not an estimated Daisychain multiplier.

## Parallels with effective human teams

### Shared goals and working agreements

[Mathieu and Rapp (2009)](https://doi.org/10.1037/a0013257) studied 32 MBA teams in a business simulation. Strong performance strategies, alongside high-quality team charters, were associated with stronger sustained performance. This bounded study does not establish that adding a template causes improvement in every team.

**Design implication:** start with a brief that makes the objective, criteria, responsibilities, constraints, and stopping conditions explicit. For agents, whether the brief improves outcomes remains an empirical question.

### Unique information and premature consensus

[Stasser and Titus (1985)](https://doi.org/10.1037/0022-3514.48.6.1467) found that discussion in a simulated candidate-selection task disproportionately reflected shared information and existing preferences. Groups often failed to combine the uniquely held information needed for a better decision.

**Design implication:** gather initial observations before sharing proposed answers, and preserve unique or disconfirming evidence through handoffs. This is an analogy to a human experiment; it does not establish the mechanism of LLM agreement or guarantee independent agent errors.

### Psychological safety and reporting problems

[Edmondson (1999)](https://doi.org/10.2307/2666999) studied 51 manufacturing teams. Psychological safety was associated with team learning behavior; the tested model linked learning behavior with performance. The field study was observational, rather than randomized causal evidence.

**Design implication:** explicitly allow uncertainty, failed tests, disagreement, and reports that a change made the result worse. Agents do not experience human psychological safety. The corresponding design choices are reporting rules, evaluation incentives, and tools that preserve evidence.

### Participation and collective intelligence

[Woolley and colleagues (2010)](https://doi.org/10.1126/science.1193147) studied 699 people in groups of two to five. A general factor of collective performance was associated with social sensitivity and a more even distribution of conversational turns. The associations do not prove that enforcing equal airtime causes better performance.

**Design implication:** give relevant specialists an explicit opportunity to contribute evidence. Equal token quotas or adding more agents do not follow from this study.

### Debriefing and learning from outcomes

[Tannenbaum and Cerasoli (2013)](https://doi.org/10.1177/0018720812448394) synthesized 46 samples involving 2,136 participants and found better effectiveness for debriefs relative to controls, with an average effect of d = 0.67. The authors' approximate 20–25% interpretation applies to the human settings studied, not to Daisychain or AI agents.

**Design implication:** finish the regrade with a short debrief: what was expected, what happened, what evidence explains the difference, and what should change next time. Keep persistent lessons only within the user's authorization.

## Improvements motivated by these connections

The public skill includes the following design choices. Their value should be measured rather than assumed.

| Choice | Intended benefit | What to check |
| --- | --- | --- |
| Stable acceptance criteria | Reduce goal drift and moving evaluation standards | Whether original requirements survive the handoffs |
| Artifact-first review | Reduce anchoring on a persuasive explanation | Valid defects caught and missed |
| Counterevidence in handoffs | Prevent useful disagreement from disappearing | Whether contradictory findings reach the final decision |
| Grades alongside observable checks | Distinguish opinion from demonstrated behavior | Task completion, relevant checks, and regressions |
| Effort budgets and adaptive delegation | Control coordination overhead | Quality relative to time, tokens, and human effort |
| Structured final debrief | Learn from failed assumptions | Whether a proposed lesson holds on later tasks |

Fresh context can reduce some information leakage, but agents may still share models, training, prompts, and blind spots. Tests can also miss defects. An effective workflow needs evidence beyond agreement among reviewers.

The [first comparison against a simpler baseline](../benchmarks/results/2026-11-11-pilot/RESULTS.md) reached a functional-quality ceiling on four synthetic task families, with higher time and estimated cost for the chain. Broader claims require [additional evaluation](evaluation.md), followed by selective improvements supported by observed failures.
