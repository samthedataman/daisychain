# Exploratory benchmark results

Model: `gpt-6.1-sol`; reasoning: `low`; CLI: `codex-cli 0.162.1`. Run started: 2026-11-11T06:30:21.690806+00:00.

This compares one normal coding-agent session with one fixed four-stage Daisychain round. It is a natural-workflow comparison, not an equal-token-budget experiment. All scheduled failures and recorded incomplete workflows remain in the results.

| Metric | Single agent | Daisychain |
| --- | ---: | ---: |
| Scheduled / observed attempts | 12 / 12 | 12 / 12 |
| Completed workflows | 12/12 | 12/12 |
| Task success (completed + every check passed) | 12/12 (100.0%) | 12/12 (100.0%) |
| Solutions passing every check, regardless of workflow completion | 12 | 12 |
| Public smoke suites passed / observed | 12/12 | 12/12 |
| Mean held-out check-pass fraction (equal task weight) | 100.0% | 100.0% |
| Mean workflow seconds | 52.62 | 206.38 |
| Median workflow seconds | 50.35 | 183.68 |
| Total estimated Standard credits | 13.3445 | 43.6998 |
| Mean estimated Standard credits / observed attempt | 1.1120 | 3.6416 |
| Attempts with complete usage | 12/12 | 12/12 |

Schedule coverage is complete; every frozen schedule identity has one recorded attempt.

Matched pairs: 12; unmatched pair keys: 0. Both succeed: 12; single-only successes: 0; Daisychain-only successes: 0; both fail: 0.

Daisychain/single paired latency ratios: mean 4.05×, median 3.54× (12 pairs). Mean paired latency difference: 153.77 seconds. Paired estimated-credit ratios: mean 3.35×, median 3.14× (12 pairs with complete usage and a nonzero baseline cost). These average per-pair ratios, rather than dividing the overall means.

## Per-task results

| Task | Condition | Successes / attempts | Mean held-out checks passed | Mean seconds | Mean estimated credits |
| --- | --- | ---: | ---: | ---: | ---: |
| csv_import | Single agent | 3/3 | 100.0% | 55.34 | 1.0868 |
| csv_import | Daisychain | 3/3 | 100.0% | 197.47 | 3.5887 |
| event_reconcile | Single agent | 3/3 | 100.0% | 56.20 | 1.1153 |
| event_reconcile | Daisychain | 3/3 | 100.0% | 174.27 | 3.4298 |
| query_patch | Single agent | 3/3 | 100.0% | 41.64 | 0.9449 |
| query_patch | Daisychain | 3/3 | 100.0% | 268.15 | 3.6416 |
| ttl_cache | Single agent | 3/3 | 100.0% | 57.28 | 1.3011 |
| ttl_cache | Daisychain | 3/3 | 100.0% | 185.64 | 3.9065 |

## Stage breakdown (secondary diagnostic)

These call-level diagnostics help describe workflow overhead; they are not a new success metric. They are not added to the workflow totals above, which remain authoritative. Known credit subtotals and means are lower bounds when usage is incomplete. Stage means use reported stage timings; workflow means also include inter-stage overhead.

| Condition | Stage | Calls | Mean reported seconds | Timings observed | Known estimated credits subtotal | Known credits / call | Complete usage |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Single agent | single | 12 | 52.61 | 12/12 | 13.3445 | 1.1120 | 12/12 |
| Daisychain | grade | 12 | 50.32 | 12/12 | 12.0195 | 1.0016 | 12/12 |
| Daisychain | propose | 12 | 54.27 | 12/12 | 6.5158 | 0.5430 | 12/12 |
| Daisychain | implement | 12 | 49.09 | 12/12 | 13.9316 | 1.1610 | 12/12 |
| Daisychain | regrade | 12 | 52.67 | 12/12 | 11.2329 | 0.9361 | 12/12 |

## Every recorded attempt

| Attempt / final solution | Condition | Workflow complete | Task success | Public smoke tests | Held-out checks | Seconds | Estimated credits |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| [01-ttl_cache-r2-daisychain](artifacts/01-ttl_cache-r2-daisychain/solution.py) | Daisychain | yes | yes | pass | 14/14 | 184.39 | 4.0377 |
| [02-ttl_cache-r2-single](artifacts/02-ttl_cache-r2-single/solution.py) | Single agent | yes | yes | pass | 14/14 | 64.55 | 1.3146 |
| [03-event_reconcile-r1-daisychain](artifacts/03-event_reconcile-r1-daisychain/solution.py) | Daisychain | yes | yes | pass | 16/16 | 162.99 | 3.0454 |
| [04-event_reconcile-r1-single](artifacts/04-event_reconcile-r1-single/solution.py) | Single agent | yes | yes | pass | 16/16 | 47.17 | 1.0577 |
| [05-query_patch-r1-single](artifacts/05-query_patch-r1-single/solution.py) | Single agent | yes | yes | pass | 14/14 | 37.56 | 0.7195 |
| [06-query_patch-r1-daisychain](artifacts/06-query_patch-r1-daisychain/solution.py) | Daisychain | yes | yes | pass | 14/14 | 164.63 | 3.2159 |
| [07-ttl_cache-r1-daisychain](artifacts/07-ttl_cache-r1-daisychain/solution.py) | Daisychain | yes | yes | pass | 14/14 | 182.98 | 3.6623 |
| [08-ttl_cache-r1-single](artifacts/08-ttl_cache-r1-single/solution.py) | Single agent | yes | yes | pass | 14/14 | 50.45 | 1.1613 |
| [09-csv_import-r2-daisychain](artifacts/09-csv_import-r2-daisychain/solution.py) | Daisychain | yes | yes | pass | 16/16 | 209.07 | 3.7539 |
| [10-csv_import-r2-single](artifacts/10-csv_import-r2-single/solution.py) | Single agent | yes | yes | pass | 16/16 | 61.22 | 1.1457 |
| [11-csv_import-r1-daisychain](artifacts/11-csv_import-r1-daisychain/solution.py) | Daisychain | yes | yes | pass | 16/16 | 200.69 | 3.6892 |
| [12-csv_import-r1-single](artifacts/12-csv_import-r1-single/solution.py) | Single agent | yes | yes | pass | 16/16 | 48.61 | 1.0485 |
| [13-event_reconcile-r3-single](artifacts/13-event_reconcile-r3-single/solution.py) | Single agent | yes | yes | pass | 16/16 | 72.80 | 0.9440 |
| [14-event_reconcile-r3-daisychain](artifacts/14-event_reconcile-r3-daisychain/solution.py) | Daisychain | yes | yes | pass | 16/16 | 162.15 | 3.6211 |
| [15-csv_import-r3-single](artifacts/15-csv_import-r3-single/solution.py) | Single agent | yes | yes | pass | 16/16 | 56.20 | 1.0662 |
| [16-csv_import-r3-daisychain](artifacts/16-csv_import-r3-daisychain/solution.py) | Daisychain | yes | yes | pass | 16/16 | 182.65 | 3.3230 |
| [17-ttl_cache-r3-single](artifacts/17-ttl_cache-r3-single/solution.py) | Single agent | yes | yes | pass | 14/14 | 56.84 | 1.4275 |
| [18-ttl_cache-r3-daisychain](artifacts/18-ttl_cache-r3-daisychain/solution.py) | Daisychain | yes | yes | pass | 14/14 | 189.56 | 4.0193 |
| [19-query_patch-r3-single](artifacts/19-query_patch-r3-single/solution.py) | Single agent | yes | yes | pass | 14/14 | 37.10 | 1.0088 |
| [20-query_patch-r3-daisychain](artifacts/20-query_patch-r3-daisychain/solution.py) | Daisychain | yes | yes | pass | 14/14 | 161.43 | 4.4902 |
| [21-query_patch-r2-daisychain](artifacts/21-query_patch-r2-daisychain/solution.py) | Daisychain | yes | yes | pass | 14/14 | 478.40 | 3.2188 |
| [22-query_patch-r2-single](artifacts/22-query_patch-r2-single/solution.py) | Single agent | yes | yes | pass | 14/14 | 50.26 | 1.1065 |
| [23-event_reconcile-r2-single](artifacts/23-event_reconcile-r2-single/solution.py) | Single agent | yes | yes | pass | 16/16 | 48.62 | 1.3442 |
| [24-event_reconcile-r2-daisychain](artifacts/24-event_reconcile-r2-daisychain/solution.py) | Daisychain | yes | yes | pass | 16/16 | 197.67 | 3.6230 |

## Measurement and interpretation

Credit estimate: `(input − cached input) × 50 + cached input × 2.5 + output × 250`, divided by 1,000,000. Cached input is a subset of input; reasoning is not added again to output. Rates were checked 2026-11-11: [official Codex pricing](https://learn.chatgpt.com/docs/pricing#token-rates). Actual subscription consumption, purchased credits and dollar billing were not observed. Incomplete usage yields a lower-bound subtotal and an unknown full cost, never a claim of zero cost.

Workflow time includes CLI startup, model calls, tools and handoffs; final held-out scoring is excluded. Latency includes failed attempts. The secondary check-pass metric uses held-out checks only, averaged within each task, then across tasks. Overall task success additionally requires the public smoke tests. Missing evaluation coverage, unrecorded scheduled attempts or unmatched pairs must be resolved or reported as a partial run; they are not silently counted as successes.

This is a small descriptive benchmark of synthetic Python repairs on one model/configuration. Repeated attempts reuse the same task families and are not independent task types. A tie at full quality is a ceiling effect, not evidence of equivalent performance on harder tasks. These results cannot establish general superiority, UI usability, or production reliability.

[Manifest and frozen schedule](manifest.json) · [Per-check results and usage](results.json) · [Machine-readable summary](summary.json) · [Attempt CSV](runs.csv) · [Protocol](../../protocol.md)
