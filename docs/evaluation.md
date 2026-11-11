# How to evaluate Daisychain

The [first comparative pilot](../benchmarks/results/2026-11-11-pilot/RESULTS.md) found a full functional-quality tie with higher time and estimated cost for one-round Daisychain on four synthetic Python task families. It does not establish a performance gain or equivalence on harder work. Evaluate additional configurations against a simpler baseline before increasing agent count or review rounds.

## A practical comparison

1. Collect a set of representative, sanitized tasks with starting artifacts and acceptance criteria. Include easy tasks where delegation may add overhead and harder tasks where review could help.
2. Compare a single agent with normal self-review against Daisychain using fresh copies of the same starting artifact. Match model/tool access and permissions. Record both a comparable resource-budget condition and actual resource use.
3. Randomize run order and repeat tasks because model outputs vary. Keep evaluation items or tests separate from implementation context when feasible.
4. Have a reviewer who does not know the condition assess outcomes. Prefer automated acceptance checks and actual task completion over agent-assigned grades. Human usability studies are needed for claims about real user success.
5. Record quality, regressions, elapsed time, token/cost data when exposed, and human intervention. Report incomplete, blocked, and failed runs alongside successes.
6. Publish the method, model and harness versions, sample size, per-task results, and uncertainty. Label small exploratory results accordingly. Draw conclusions only within the tested tasks and conditions.

## Outcomes worth measuring

| Measure | Example |
| --- | --- |
| Task success | Acceptance criteria satisfied; user can complete the intended workflow |
| Correctness | Relevant checks pass; no introduced regressions |
| Review usefulness | Valid defects caught, false alarms, and defects missed |
| Efficiency | Time, tokens, monetary cost, and number of rounds |
| Coordination | Dropped requirements, conflicting edits, repeated work, lost evidence |
| Human effort | Clarifications, corrections, or manual fixes needed |

Compare independent review with shared-context review, and fixed role chains with adaptive delegation. Different models are another experimental condition, not a guarantee of independence. Use these comparisons to discover which steps earn their cost.

## Improvement roadmap

- Use harder, independently sourced tasks after the pilot's quality ceiling; keep the new protocol separate from the existing results.
- Compare a shared inference budget and a predefined adaptive repair loop with the current natural-workflow, one-round condition.
- Calibrate the rubric using examples that reviewers can score consistently.
- Retain counterevidence in handoffs and measure whether it changes defect detection.
- Test whether a reviewer seeing the artifact before the implementer's rationale reduces missed defects.
- Add a machine-readable run record or harness adapter only when real integrations justify maintaining it.
- Keep successful, sanitized examples and failed cases with enough context to reproduce the result.

Avoid optimizing the workflow toward its own evaluator's tastes. A rising grade with unchanged task completion is a measurement problem to investigate.
