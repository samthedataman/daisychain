#!/usr/bin/env python3
"""Aggregate benchmark records without model calls or third-party packages."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
from statistics import mean, median

CONDITIONS = ("single", "daisychain")
LABELS = {"single": "Single agent", "daisychain": "Daisychain"}
CORE_USAGE = ("input_tokens", "cached_input_tokens", "output_tokens")


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def estimated_credits(usage: dict, pricing: dict) -> float | None:
    """Price a known usage subtotal; None means core usage is not available."""
    if not all(key in usage for key in CORE_USAGE):
        return None
    values = {key: _number(usage[key], key) for key in CORE_USAGE}
    if values["cached_input_tokens"] > values["input_tokens"]:
        raise ValueError("cached_input_tokens cannot exceed input_tokens")
    rates = {key: _number(pricing[key], key) for key in (
        "per_million_uncached_input", "per_million_cached_input", "per_million_output")}
    return ((values["input_tokens"] - values["cached_input_tokens"]) * rates["per_million_uncached_input"]
            + values["cached_input_tokens"] * rates["per_million_cached_input"]
            + values["output_tokens"] * rates["per_million_output"]) / 1_000_000


def _average(values):
    return mean(values) if values else None


def _median(values):
    return median(values) if values else None


def normalize(record: dict, pricing: dict) -> dict:
    evaluation = record.get("evaluation", {})
    total, passed = evaluation.get("total"), evaluation.get("passed")
    public_ok = evaluation.get("public_tests_pass")
    if public_ok is not None and not isinstance(public_ok, bool):
        raise ValueError("evaluation.public_tests_pass must be a boolean when supplied")
    check_fraction = None
    if total is not None or passed is not None:
        if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
            raise ValueError("evaluation.total must be a positive integer")
        if not isinstance(passed, int) or isinstance(passed, bool) or not 0 <= passed <= total:
            raise ValueError("evaluation.passed must be an integer between zero and total")
        check_fraction = passed / total
    solution_pass = check_fraction == 1 and public_ok is True
    if bool(evaluation.get("task_pass")) != solution_pass:
        raise ValueError("evaluation.task_pass contradicts held-out counts or public smoke evidence")
    success = bool(record.get("workflow_completed") and solution_pass)
    if "task_success" in record and bool(record["task_success"]) != success:
        raise ValueError("task_success contradicts workflow completion/evaluation")
    usage = record.get("usage") or {}
    for key, value in usage.items():
        _number(value, key)
    known_cost = estimated_credits(usage, pricing)
    usage_complete = bool(record.get("usage_complete") and known_cost is not None)
    return {"record": record, "condition": record["condition"], "task_id": record["task_id"],
            "repetition": record["repetition"], "task_success": success,
            "workflow_completed": bool(record.get("workflow_completed")),
            "solution_pass": solution_pass,
            "public_tests_pass": public_ok,
            "check_fraction": check_fraction, "passed": passed, "total": total,
            "elapsed_seconds": _number(record["elapsed_seconds"], "elapsed_seconds"),
            "known_estimated_credits": known_cost,
            "estimated_credits": known_cost if usage_complete else None,
            "usage_complete": usage_complete, "usage": usage}


def _group(rows: list[dict], scheduled: int | None = None) -> dict:
    per_task = defaultdict(list)
    tokens = Counter()
    for row in rows:
        if row["check_fraction"] is not None:
            per_task[row["task_id"]].append(row["check_fraction"])
        tokens.update(row["usage"])
    count = len(rows)
    costs_complete = bool(rows) and all(row["usage_complete"] for row in rows)
    known_cost = sum(row["known_estimated_credits"] or 0 for row in rows)
    result = {
        "scheduled_attempts": scheduled,
        "observed_attempts": count,
        "unrecorded_attempts": max(0, scheduled - count) if scheduled is not None else None,
        "workflow_completed": sum(row["workflow_completed"] for row in rows),
        "task_successes": sum(row["task_success"] for row in rows),
        "task_success_rate": sum(row["task_success"] for row in rows) / count if count else None,
        "solution_passes": sum(row["solution_pass"] for row in rows),
        "public_tests_passes": sum(row["public_tests_pass"] is True for row in rows),
        "public_tests_observations": sum(row["public_tests_pass"] is not None for row in rows),
        "check_fraction_observations": sum(row["check_fraction"] is not None for row in rows),
        "tasks_with_check_results": len(per_task),
        "mean_check_pass_fraction": _average([mean(values) for values in per_task.values()]),
        "mean_elapsed_seconds": _average([row["elapsed_seconds"] for row in rows]),
        "median_elapsed_seconds": _median([row["elapsed_seconds"] for row in rows]),
        "total_elapsed_seconds": sum(row["elapsed_seconds"] for row in rows),
        "usage_complete_attempts": sum(row["usage_complete"] for row in rows),
        "usage_complete": costs_complete,
        "known_token_totals": dict(tokens),
        "known_estimated_credits_total": known_cost,
        "known_estimated_credits_mean_lower_bound": known_cost / count if count else None,
        "estimated_credits_total": known_cost if costs_complete else None,
        "estimated_credits_mean": known_cost / count if costs_complete else None,
    }
    return result


def _stage_breakdown(records: list[dict], pricing: dict) -> dict:
    """Secondary diagnostics only; these subtotals never feed workflow metrics."""
    grouped = {condition: defaultdict(list) for condition in CONDITIONS}
    for record in records:
        for stage in record.get("stages") or []:
            if not isinstance(stage, dict):
                continue
            grouped[record["condition"]][stage.get("stage") or "unknown"].append(stage)
    result = {condition: {} for condition in CONDITIONS}
    order = {name: index for index, name in enumerate(("single", "grade", "propose", "implement", "regrade"))}
    for condition, groups in grouped.items():
        for name in sorted(groups, key=lambda stage: (order.get(stage, len(order)), stage)):
            stages = groups[name]
            elapsed, tokens, costs, complete = [], Counter(), [], []
            for stage in stages:
                if stage.get("elapsed_seconds") is not None:
                    elapsed.append(_number(stage["elapsed_seconds"], "stage.elapsed_seconds"))
                usage = stage.get("usage") or {}
                for key, value in usage.items():
                    _number(value, key)
                tokens.update(usage)
                cost = estimated_credits(usage, pricing)
                costs.append(cost or 0)
                # A failed call with only partial telemetry retains a known subtotal.
                complete.append(bool(stage.get("usage_complete", stage.get("completed", False)))
                                and cost is not None)
            known_cost = sum(costs)
            all_complete = all(complete)
            result[condition][name] = {
                "calls": len(stages),
                "completed_calls": sum(bool(stage.get("completed")) for stage in stages),
                "elapsed_observations": len(elapsed),
                "mean_elapsed_seconds": _average(elapsed),
                "usage_complete_calls": sum(complete),
                "usage_complete": all_complete,
                "known_token_totals": dict(tokens),
                "known_estimated_credits_total": known_cost,
                "known_estimated_credits_mean_lower_bound": known_cost / len(stages),
                "estimated_credits_total": known_cost if all_complete else None,
                "estimated_credits_mean": known_cost / len(stages) if all_complete else None,
            }
    return result


def summarize(manifest: dict, records: list[dict]) -> dict:
    rows = [normalize(record, manifest["pricing"]) for record in records]
    identities = set()
    for row in rows:
        if row["condition"] not in CONDITIONS:
            raise ValueError(f"unknown condition: {row['condition']}")
        identity = (row["task_id"], row["repetition"], row["condition"])
        if identity in identities:
            raise ValueError(f"duplicate attempt: {identity}")
        identities.add(identity)
    schedule = manifest.get("schedule")
    if not isinstance(schedule, list):
        raise ValueError("manifest.schedule must contain the frozen attempt schedule")
    scheduled_identities = set()
    for item in schedule:
        identity = (item["task_id"], item["repetition"], item["condition"])
        if item["condition"] not in CONDITIONS:
            raise ValueError(f"unknown scheduled condition: {item['condition']}")
        if identity in scheduled_identities:
            raise ValueError(f"duplicate scheduled attempt: {identity}")
        scheduled_identities.add(identity)
    unexpected = identities - scheduled_identities
    if unexpected:
        raise ValueError(f"unscheduled observed attempts: {sorted(unexpected)}")
    missing = [{key: item[key] for key in ("task_id", "repetition", "condition")}
               for item in schedule if (item["task_id"], item["repetition"], item["condition"]) not in identities]
    planned = Counter(item["condition"] for item in schedule)
    by_condition = {condition: _group([row for row in rows if row["condition"] == condition],
                    planned[condition]) for condition in CONDITIONS}
    tasks = sorted({row["task_id"] for row in rows} | {item["task_id"] for item in schedule})
    by_task = {task: {condition: _group([row for row in rows if row["condition"] == condition
                        and row["task_id"] == task], sum(item["condition"] == condition and
                            item["task_id"] == task for item in schedule))
                    for condition in CONDITIONS} for task in tasks}
    pairs = defaultdict(dict)
    for row in rows:
        pairs[(row["task_id"], row["repetition"])][row["condition"]] = row
    pair_rows = []
    for (task, repetition), arms in sorted(pairs.items()):
        if len(arms) != 2:
            continue
        single, chain = arms["single"], arms["daisychain"]
        speed_ratio = chain["elapsed_seconds"] / single["elapsed_seconds"] if single["elapsed_seconds"] else None
        cost_ratio = (chain["estimated_credits"] / single["estimated_credits"]
                      if single["estimated_credits"] and chain["estimated_credits"] is not None else None)
        pair_rows.append({"task_id": task, "repetition": repetition,
            "single_success": single["task_success"], "daisychain_success": chain["task_success"],
            "latency_ratio_daisychain_over_single": speed_ratio,
            "latency_difference_seconds": chain["elapsed_seconds"] - single["elapsed_seconds"],
            "estimated_credits_ratio_daisychain_over_single": cost_ratio})
    speeds = [pair["latency_ratio_daisychain_over_single"] for pair in pair_rows
              if pair["latency_ratio_daisychain_over_single"] is not None]
    costs = [pair["estimated_credits_ratio_daisychain_over_single"] for pair in pair_rows
             if pair["estimated_credits_ratio_daisychain_over_single"] is not None]
    return {"schema_version": 1, "conditions": by_condition, "tasks": by_task,
        "schedule_coverage": {"scheduled_attempts": len(schedule), "observed_attempts": len(rows),
            "complete": not missing, "unrecorded_attempts": missing},
        "stage_breakdown": _stage_breakdown(records, manifest["pricing"]),
        "paired": {"matched_pairs": len(pair_rows), "unmatched_pair_keys": len(pairs) - len(pair_rows),
            "latency_ratio_pairs": len(speeds), "mean_latency_ratio": _average(speeds),
            "median_latency_ratio": _median(speeds),
            "mean_latency_difference_seconds": _average([p["latency_difference_seconds"] for p in pair_rows]),
            "complete_credit_ratio_pairs": len(costs), "mean_estimated_credits_ratio": _average(costs),
            "median_estimated_credits_ratio": _median(costs),
            "both_succeed": sum(p["single_success"] and p["daisychain_success"] for p in pair_rows),
            "single_only_succeeds": sum(p["single_success"] and not p["daisychain_success"] for p in pair_rows),
            "daisychain_only_succeeds": sum(p["daisychain_success"] and not p["single_success"] for p in pair_rows),
            "both_fail": sum(not p["single_success"] and not p["daisychain_success"] for p in pair_rows),
            "pairs": pair_rows},
        "cost_basis": "Estimated Standard Codex credits, not observed billing or a dollar invoice",
        "check_metric": "Mean of within-task mean check-pass fractions; tasks equally weighted"}


def _fmt(value, places=2):
    return f"{value:.{places}f}" if value is not None else "unknown"


def _pct(value):
    return f"{value:.1%}" if value is not None else "unknown"


def _credit_cell(group, mean_value=False):
    key = "estimated_credits_mean" if mean_value else "estimated_credits_total"
    lower = "known_estimated_credits_mean_lower_bound" if mean_value else "known_estimated_credits_total"
    if group[key] is not None:
        return _fmt(group[key], 4)
    return f"≥{_fmt(group[lower], 4)}; full cost unknown"


def render_markdown(summary: dict, manifest: dict, records: list[dict]) -> str:
    a, b = (summary["conditions"][condition] for condition in CONDITIONS)
    lines = ["# Exploratory benchmark results", "",
        f"Model: `{manifest.get('model', 'unknown')}`; reasoning: `{manifest.get('reasoning_effort', 'unknown')}`; "
        f"CLI: `{manifest.get('codex_version', 'unknown')}`. Run started: {manifest.get('started_utc', 'unknown')}.", "",
        "This compares one normal coding-agent session with one fixed four-stage Daisychain round. "
        "It is a natural-workflow comparison, not an equal-token-budget experiment. "
        "All scheduled failures and recorded incomplete workflows remain in the results.", "",
        "| Metric | Single agent | Daisychain |", "| --- | ---: | ---: |"]
    metrics = [
        ("Scheduled / observed attempts", f"{a['scheduled_attempts']} / {a['observed_attempts']}", f"{b['scheduled_attempts']} / {b['observed_attempts']}"),
        ("Completed workflows", f"{a['workflow_completed']}/{a['observed_attempts']}", f"{b['workflow_completed']}/{b['observed_attempts']}"),
        ("Task success (completed + every check passed)", f"{a['task_successes']}/{a['observed_attempts']} ({_pct(a['task_success_rate'])})", f"{b['task_successes']}/{b['observed_attempts']} ({_pct(b['task_success_rate'])})"),
        ("Solutions passing every check, regardless of workflow completion", str(a['solution_passes']), str(b['solution_passes'])),
        ("Public smoke suites passed / observed", f"{a['public_tests_passes']}/{a['public_tests_observations']}", f"{b['public_tests_passes']}/{b['public_tests_observations']}"),
        ("Mean held-out check-pass fraction (equal task weight)", _pct(a['mean_check_pass_fraction']), _pct(b['mean_check_pass_fraction'])),
        ("Mean workflow seconds", _fmt(a['mean_elapsed_seconds']), _fmt(b['mean_elapsed_seconds'])),
        ("Median workflow seconds", _fmt(a['median_elapsed_seconds']), _fmt(b['median_elapsed_seconds'])),
        ("Total estimated Standard credits", _credit_cell(a), _credit_cell(b)),
        ("Mean estimated Standard credits / observed attempt", _credit_cell(a, True), _credit_cell(b, True)),
        ("Attempts with complete usage", f"{a['usage_complete_attempts']}/{a['observed_attempts']}", f"{b['usage_complete_attempts']}/{b['observed_attempts']}"),
    ]
    lines.extend(f"| {label} | {left} | {right} |" for label, left, right in metrics)
    missing = summary["schedule_coverage"]["unrecorded_attempts"]
    if missing:
        descriptions = [f"`{item['task_id']}-r{item['repetition']}-{item['condition']}`" for item in missing]
        lines += ["", "**Partial schedule:** unrecorded scheduled attempts: " + ", ".join(descriptions) + "."]
    else:
        lines += ["", "Schedule coverage is complete; every frozen schedule identity has one recorded attempt."]
    p = summary["paired"]
    lines += ["", f"Matched pairs: {p['matched_pairs']}; unmatched pair keys: {p['unmatched_pair_keys']}. "
        f"Both succeed: {p['both_succeed']}; single-only successes: {p['single_only_succeeds']}; "
        f"Daisychain-only successes: {p['daisychain_only_succeeds']}; both fail: {p['both_fail']}.", "",
        f"Daisychain/single paired latency ratios: mean {_fmt(p['mean_latency_ratio'])}×, "
        f"median {_fmt(p['median_latency_ratio'])}× ({p['latency_ratio_pairs']} pairs). "
        f"Mean paired latency difference: {_fmt(p['mean_latency_difference_seconds'])} seconds. "
        f"Paired estimated-credit ratios: mean {_fmt(p['mean_estimated_credits_ratio'])}×, "
        f"median {_fmt(p['median_estimated_credits_ratio'])}× "
        f"({p['complete_credit_ratio_pairs']} pairs with complete usage and a nonzero baseline cost). "
        "These average per-pair ratios, rather than dividing the overall means.", "",
        "## Per-task results", "",
        "| Task | Condition | Successes / attempts | Mean held-out checks passed | Mean seconds | Mean estimated credits |",
        "| --- | --- | ---: | ---: | ---: | ---: |"]
    for task, arms in summary["tasks"].items():
        for condition, group in arms.items():
            lines.append(f"| {task} | {LABELS[condition]} | {group['task_successes']}/{group['observed_attempts']} | "
                f"{_pct(group['mean_check_pass_fraction'])} | {_fmt(group['mean_elapsed_seconds'])} | {_credit_cell(group, True)} |")
    lines += ["", "## Stage breakdown (secondary diagnostic)", "",
        "These call-level diagnostics help describe workflow overhead; they are not a new success metric. "
        "They are not added to the workflow totals above, which remain authoritative. "
        "Known credit subtotals and means are lower bounds when usage is incomplete. "
        "Stage means use reported stage timings; workflow means also include inter-stage overhead.", "",
        "| Condition | Stage | Calls | Mean reported seconds | Timings observed | Known estimated credits subtotal | Known credits / call | Complete usage |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    stage_rows = 0
    for condition, stages in summary["stage_breakdown"].items():
        for name, group in stages.items():
            stage_rows += 1
            lines.append(f"| {LABELS[condition]} | {name} | {group['calls']} | "
                f"{_fmt(group['mean_elapsed_seconds'])} | {group['elapsed_observations']}/{group['calls']} | "
                f"{_fmt(group['known_estimated_credits_total'], 4)} | "
                f"{_fmt(group['known_estimated_credits_mean_lower_bound'], 4)} | "
                f"{group['usage_complete_calls']}/{group['calls']} |")
    if not stage_rows:
        lines += ["", "No stage-level records were supplied; workflow metrics are unchanged."]
    lines += ["", "## Every recorded attempt", "",
        "| Attempt / final solution | Condition | Workflow complete | Task success | Public smoke tests | Held-out checks | Seconds | Estimated credits |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: |"]
    for record in records:
        row = normalize(record, manifest["pricing"])
        identifier = record.get("id", f"{row['task_id']}-r{row['repetition']}-{row['condition']}")
        artifact = record.get("artifact_directory")
        link = f"[{identifier}]({artifact}/solution.py)" if artifact else identifier
        check = f"{row['passed']}/{row['total']}" if row['total'] is not None else "unknown"
        cost = (_fmt(row['estimated_credits'], 4) if row['usage_complete'] else
                f"≥{_fmt(row['known_estimated_credits'] or 0, 4)}; unknown total")
        public_status = "unknown" if row['public_tests_pass'] is None else "pass" if row['public_tests_pass'] else "fail"
        lines.append(f"| {link} | {LABELS[row['condition']]} | {'yes' if row['workflow_completed'] else 'no'} | "
            f"{'yes' if row['task_success'] else 'no'} | {public_status} | {check} | {_fmt(row['elapsed_seconds'])} | {cost} |")
    pricing = manifest["pricing"]
    lines += ["", "## Measurement and interpretation", "",
        f"Credit estimate: `(input − cached input) × {pricing['per_million_uncached_input']} + "
        f"cached input × {pricing['per_million_cached_input']} + output × {pricing['per_million_output']}`, "
        "divided by 1,000,000. Cached input is a subset of input; reasoning is not added again to output. "
        f"Rates were checked {pricing.get('checked_date', 'unknown')}: "
        f"[official Codex pricing]({pricing.get('source', 'https://learn.chatgpt.com/docs/pricing')}). "
        "Actual subscription consumption, purchased credits and dollar billing were not observed. "
        "Incomplete usage yields a lower-bound subtotal and an unknown full cost, never a claim of zero cost.", "",
        "Workflow time includes CLI startup, model calls, tools and handoffs; final held-out scoring is excluded. "
        "Latency includes failed attempts. The secondary check-pass metric uses held-out checks only, "
        "averaged within each task, then across tasks. Overall task success additionally requires the public smoke tests. "
        "Missing evaluation coverage, unrecorded scheduled attempts or unmatched pairs must be resolved or "
        "reported as a partial run; they are not silently counted as successes.", "",
        "This is a small descriptive benchmark of synthetic Python repairs on one model/configuration. "
        "Repeated attempts reuse the same task families and are not independent task types. "
        "A tie at full quality is a ceiling effect, not evidence of equivalent performance on harder tasks. "
        "These results cannot establish general superiority, UI usability, or production reliability.", "",
        "[Manifest and frozen schedule](manifest.json) · [Per-check results and usage](results.json) · "
        "[Machine-readable summary](summary.json) · [Attempt CSV](runs.csv) · [Protocol](../../protocol.md)", ""]
    return "\n".join(lines)


def write_outputs(directory: Path) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text())
    records = json.loads((directory / "results.json").read_text())
    summary = summarize(manifest, records)
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    fields = ["id", "task_id", "repetition", "condition", "workflow_completed", "task_success",
        "solution_pass", "public_tests_pass", "checks_passed", "checks_total", "elapsed_seconds", "usage_complete",
        "input_tokens", "cached_input_tokens", "output_tokens", "estimated_credits",
        "known_estimated_credits_lower_bound", "artifact_directory"]
    with (directory / "runs.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = normalize(record, manifest["pricing"])
            writer.writerow({"id": record.get("id"), "task_id": row["task_id"], "repetition": row["repetition"],
                "condition": row["condition"], "workflow_completed": row["workflow_completed"],
                "task_success": row["task_success"], "solution_pass": row["solution_pass"],
                "public_tests_pass": row["public_tests_pass"],
                "checks_passed": row["passed"], "checks_total": row["total"],
                "elapsed_seconds": row["elapsed_seconds"], "usage_complete": row["usage_complete"],
                **{key: row["usage"].get(key) for key in CORE_USAGE},
                "estimated_credits": row["estimated_credits"],
                "known_estimated_credits_lower_bound": row["known_estimated_credits"],
                "artifact_directory": record.get("artifact_directory")})
    (directory / "RESULTS.md").write_text(render_markdown(summary, manifest, records))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    summary = write_outputs(args.directory)
    print(json.dumps(summary["conditions"], indent=2))


if __name__ == "__main__":
    main()
