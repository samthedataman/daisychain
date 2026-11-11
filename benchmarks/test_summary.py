"""Validate measurement aggregation without calling a model."""
from copy import deepcopy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from benchmarks.summarize import estimated_credits, summarize, write_outputs


PRICING = {"per_million_uncached_input": 50, "per_million_cached_input": 2.5,
           "per_million_output": 250, "checked_date": "2026-11-11",
           "source": "https://learn.chatgpt.com/docs/pricing#token-rates"}


def record(task, rep, condition, seconds=10, passed=10, total=10, completed=True,
           usage_complete=True, usage=None):
    return {"id": f"{task}-{rep}-{condition}", "task_id": task, "repetition": rep,
            "condition": condition, "elapsed_seconds": seconds,
            "workflow_completed": completed, "usage_complete": usage_complete,
            "usage": {"input_tokens": 1000, "cached_input_tokens": 200,
                      "output_tokens": 100, "reasoning_output_tokens": 80} if usage is None else usage,
            "evaluation": {"task_pass": passed == total, "passed": passed, "total": total,
                           "public_tests_pass": True},
            "task_success": completed and passed == total,
            "artifact_directory": f"artifacts/{task}-{rep}-{condition}"}


def manifest(records):
    return {"pricing": deepcopy(PRICING), "model": "test-model", "reasoning_effort": "low",
            "codex_version": "test-cli", "started_utc": "2026-11-11T00:00:00Z",
            "schedule": [{key: row[key] for key in ("task_id", "repetition", "condition")} for row in records]}


class SummaryTests(unittest.TestCase):
    def test_cached_tokens_and_reasoning_are_not_double_counted(self):
        usage = record("a", 1, "single")["usage"]
        self.assertAlmostEqual(estimated_credits(usage, PRICING), 0.0655)
        usage["reasoning_output_tokens"] = 10_000
        self.assertAlmostEqual(estimated_credits(usage, PRICING), 0.0655)

    def test_pair_identity_is_used_instead_of_input_order(self):
        records = [record("b", 1, "daisychain", seconds=30),
                   record("a", 1, "single", seconds=10),
                   record("b", 1, "single", seconds=5),
                   record("a", 1, "daisychain", seconds=20)]
        records[0]["usage"] = {"input_tokens": 2000, "cached_input_tokens": 400, "output_tokens": 200}
        result = summarize(manifest(records), records)
        self.assertEqual(result["paired"]["matched_pairs"], 2)
        self.assertAlmostEqual(result["paired"]["mean_latency_ratio"], 4)
        self.assertAlmostEqual(result["paired"]["median_latency_ratio"], 4)
        self.assertAlmostEqual(result["paired"]["mean_estimated_credits_ratio"], 1.5)

    def test_incomplete_usage_remains_unknown_with_known_lower_bound(self):
        records = [record("a", 1, "single"), record("b", 1, "single", completed=False,
                    usage_complete=False, usage={"input_tokens": 100, "cached_input_tokens": 50, "output_tokens": 10}),
                   record("c", 1, "single", completed=False, usage_complete=False, usage={})]
        result = summarize(manifest(records), records)["conditions"]["single"]
        self.assertEqual(result["observed_attempts"], 3)
        self.assertEqual(result["task_successes"], 1)
        self.assertEqual(result["solution_passes"], 3)
        self.assertEqual(result["usage_complete_attempts"], 1)
        self.assertIsNone(result["estimated_credits_total"])
        self.assertIsNone(result["estimated_credits_mean"])
        self.assertAlmostEqual(result["known_estimated_credits_total"], 0.070625)
        self.assertEqual(result["known_token_totals"]["input_tokens"], 1100)

    def test_check_quality_weights_tasks_equally_with_unbalanced_repetitions(self):
        records = [record("a", 1, "single"), record("a", 2, "single"),
                   record("b", 1, "single", passed=0, total=4)]
        result = summarize(manifest(records), records)["conditions"]["single"]
        self.assertAlmostEqual(result["mean_check_pass_fraction"], 0.5)
        self.assertEqual(result["task_successes"], 2)

    def test_unrecorded_attempts_and_unmatched_pairs_are_visible(self):
        records = [record("a", 1, "single")]
        planned = manifest(records + [record("a", 1, "daisychain")])
        result = summarize(planned, records)
        self.assertEqual(result["conditions"]["daisychain"]["unrecorded_attempts"], 1)
        self.assertEqual(result["paired"]["matched_pairs"], 0)
        self.assertEqual(result["paired"]["unmatched_pair_keys"], 1)
        self.assertIsNone(result["conditions"]["daisychain"]["estimated_credits_total"])
        self.assertFalse(result["schedule_coverage"]["complete"])
        self.assertEqual(result["schedule_coverage"]["unrecorded_attempts"],
                         [{"task_id": "a", "repetition": 1, "condition": "daisychain"}])

    def test_unscheduled_records_and_duplicate_schedule_entries_are_rejected(self):
        original = record("a", 1, "single")
        extra = record("a", 2, "single")
        planned = manifest([original])
        with self.assertRaisesRegex(ValueError, "unscheduled observed"):
            summarize(planned, [original, extra])
        planned["schedule"].append(deepcopy(planned["schedule"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate scheduled"):
            summarize(planned, [original])
        with self.assertRaisesRegex(ValueError, "unscheduled observed"):
            summarize({"pricing": PRICING, "schedule": []}, [original])
        with self.assertRaisesRegex(ValueError, "frozen attempt schedule"):
            summarize({"pricing": PRICING}, [original])

    def test_duplicate_or_contradictory_records_fail_loudly(self):
        row = record("a", 1, "single")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            summarize(manifest([row, row]), [row, row])
        row["evaluation"]["passed"] = 9
        with self.assertRaisesRegex(ValueError, "contradicts"):
            summarize(manifest([row]), [row])
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            estimated_credits({"input_tokens": 10, "cached_input_tokens": 20, "output_tokens": 1}, PRICING)

    def test_public_smoke_failure_can_fail_an_otherwise_complete_solution(self):
        row = record("a", 1, "single")
        row["evaluation"]["public_tests_pass"] = False
        row["evaluation"]["task_pass"] = False
        row["task_success"] = False
        result = summarize(manifest([row]), [row])["conditions"]["single"]
        self.assertEqual(result["task_successes"], 0)
        self.assertEqual(result["solution_passes"], 0)
        self.assertEqual(result["mean_check_pass_fraction"], 1)
        self.assertEqual(result["public_tests_observations"], 1)
        self.assertEqual(result["public_tests_passes"], 0)

    def test_missing_public_smoke_evidence_cannot_count_as_success(self):
        row = record("a", 1, "single")
        del row["evaluation"]["public_tests_pass"]
        with self.assertRaisesRegex(ValueError, "public smoke evidence"):
            summarize(manifest([row]), [row])
        row["evaluation"]["task_pass"] = False
        row["task_success"] = False
        group = summarize(manifest([row]), [row])["conditions"]["single"]
        self.assertEqual(group["task_successes"], 0)
        self.assertEqual(group["solution_passes"], 0)
        self.assertEqual(group["mean_check_pass_fraction"], 1)
        self.assertEqual(group["public_tests_observations"], 0)

    def test_stage_diagnostics_are_separate_from_authoritative_workflow_totals(self):
        records = [record("a", 1, "single"), record("a", 1, "daisychain", seconds=40)]
        stage_usage = {"input_tokens": 100, "cached_input_tokens": 50, "output_tokens": 10}
        records[0]["stages"] = [{"stage": "single", "completed": True,
                                 "elapsed_seconds": 8, "usage": stage_usage}]
        records[1]["stages"] = [
            {"stage": "grade", "completed": True, "elapsed_seconds": 5, "usage": stage_usage},
            {"stage": "implement", "completed": True, "elapsed_seconds": 25, "usage": stage_usage},
        ]
        result = summarize(manifest(records), records)
        grade = result["stage_breakdown"]["daisychain"]["grade"]
        self.assertEqual(grade["calls"], 1)
        self.assertEqual(grade["mean_elapsed_seconds"], 5)
        self.assertEqual(grade["usage_complete_calls"], 1)
        self.assertAlmostEqual(grade["estimated_credits_total"], 0.005125)
        # The deliberately different fixture workflow telemetry must not be replaced or doubled.
        chain = result["conditions"]["daisychain"]
        self.assertEqual(chain["mean_elapsed_seconds"], 40)
        self.assertAlmostEqual(chain["estimated_credits_total"], 0.0655)

    def test_missing_or_partial_stage_fields_do_not_become_complete_measurements(self):
        records = [record("a", 1, "daisychain"), record("a", 2, "daisychain")]
        records[0]["stages"] = [
            {"stage": "grade", "completed": True, "elapsed_seconds": 6,
             "usage": {"input_tokens": 100, "cached_input_tokens": 50, "output_tokens": 10}},
            {"stage": "grade", "completed": False, "usage": None},
            {"stage": "propose"},
        ]
        result = summarize(manifest(records), records)
        grade = result["stage_breakdown"]["daisychain"]["grade"]
        self.assertEqual(grade["calls"], 2)
        self.assertEqual(grade["elapsed_observations"], 1)
        self.assertEqual(grade["mean_elapsed_seconds"], 6)
        self.assertEqual(grade["usage_complete_calls"], 1)
        self.assertIsNone(grade["estimated_credits_total"])
        self.assertAlmostEqual(grade["known_estimated_credits_total"], 0.005125)
        self.assertAlmostEqual(grade["known_estimated_credits_mean_lower_bound"], 0.0025625)
        propose = result["stage_breakdown"]["daisychain"]["propose"]
        self.assertIsNone(propose["mean_elapsed_seconds"])
        self.assertIsNone(propose["estimated_credits_mean"])
        self.assertEqual(result["stage_breakdown"]["single"], {})

    def test_stage_diagnostic_table_is_labeled_and_missing_stages_are_disclosed(self):
        from benchmarks.summarize import render_markdown
        records = [record("a", 1, "single")]
        report = render_markdown(summarize(manifest(records), records), manifest(records), records)
        self.assertIn("Stage breakdown (secondary diagnostic)", report)
        self.assertIn("No stage-level records were supplied", report)
        self.assertIn("not added to the workflow totals", report)

    def test_writes_reproducible_json_csv_and_markdown_with_all_attempts(self):
        records = [record("a", 1, "single"),
                   record("a", 1, "daisychain", seconds=20, passed=9, completed=False,
                          usage_complete=False, usage={})]
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "manifest.json").write_text(json.dumps(manifest(records)))
            (directory / "results.json").write_text(json.dumps(records))
            expected = write_outputs(directory)
            self.assertEqual(json.loads((directory / "summary.json").read_text()), expected)
            with (directory / "runs.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]["estimated_credits"], "")
            self.assertEqual(rows[1]["task_success"], "False")
            report = (directory / "RESULTS.md").read_text()
            self.assertIn("9/10", report)
            self.assertIn("unknown total", report)
            self.assertIn("not an equal-token-budget", report)
            self.assertIn("not observed", report)
            first = (directory / "RESULTS.md").read_bytes()
            write_outputs(directory)
            self.assertEqual(first, (directory / "RESULTS.md").read_bytes())


if __name__ == "__main__":
    unittest.main()
