# Exploratory coding benchmark

Compare a single coding-agent session with one four-stage Daisychain round on identical synthetic Python repair tasks. Read the [fixed protocol](protocol.md) before interpreting or changing the experiment.

## Requirements

- Python 3.12 and Codex CLI with access to the chosen model.
- Local CLI authentication configured by the operator. This repository contains no credentials or automatic public CI model jobs. Never upload auth files or private CLI logs.
- Time and usage capacity for 60 fresh CLI sessions in the default 4-task, 3-repetition experiment. These consume real model usage; total tokens are measured rather than capped.

The runner uses Codex CLI flags supported by the recorded CLI version. Compatibility with other versions is not guaranteed. Candidate code and the bounded evaluator execute locally; this is not a sandbox for hostile submissions.

The runner snapshots the local CLI model catalog at `~/.codex/models_cache.json` to avoid model-discovery refresh timeouts and keep metadata consistent. Populate it through normal CLI use first, or supply `--model-catalog /path/to/catalog.json`. The manifest records its hash; private catalogs and authentication state are not published.

## Run

From the repository root:

```bash
python3.12 -m unittest benchmarks.test_tasks benchmarks.test_runner -v
python3.12 benchmarks/run.py --output benchmarks/results/my-run
python3.12 benchmarks/summarize.py benchmarks/results/my-run
```

The output directory must be new. The runner prints a private temporary workspace path and progress, then writes sanitized artifacts and JSON measurements. Complete all generation before held-out scoring. Reproduce a published run using its manifest's model, seed, settings and source revision; stochastic outputs may differ.

Full raw CLI events and stderr remain in the private temporary workspace for local audit. Inspect sanitization before publishing. Public artifacts include exact prompts, responses, selected usage/tool-event records, candidate solutions and diffs. Read-only role sessions do not have permission to alter the candidate.

`tasks.py` holds the requirements, starting source, public tests, reference fixtures and withheld checks. `test_tasks.py` confirms reference behavior, seeded failures, smoke tests and evaluator failure handling. Public tests intentionally cover only a subset of requirements; passing them alone is insufficient.

The suite covers TTL/LRU caching, URL query updates, versioned event reconciliation and typed CSV input. It measures these repairs, not product usability or broad software-engineering ability.
