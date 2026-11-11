"""Behavioral checks for evaluator fixtures; no model calls are made."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from benchmarks.tasks import TASKS, evaluate, materialize


class TaskSuiteTests(unittest.TestCase):
    def test_reference_solutions_pass_every_held_out_check(self):
        for task_id, task in TASKS.items():
            with self.subTest(task=task_id), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "solution.py"
                path.write_text(task.reference_source, encoding="utf-8")
                result = evaluate(task_id, path)
                self.assertTrue(result["task_pass"], result)
                self.assertTrue(result["public_tests_pass"], result)
                self.assertEqual(result["public_tests_run"], 2)
                self.assertGreaterEqual(result["total"], 12)

    def test_seeded_defects_fail_held_out_checks(self):
        for task_id, task in TASKS.items():
            with self.subTest(task=task_id), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "solution.py"
                path.write_text(task.starting_source, encoding="utf-8")
                result = evaluate(task_id, path)
                self.assertFalse(result["task_pass"], result)
                self.assertTrue(result["public_tests_pass"], result)
                self.assertLess(result["passed"], result["total"])

    def test_public_smoke_tests_pass_seed_and_reference(self):
        for task_id, task in TASKS.items():
            for label, source in (("seed", task.starting_source), ("reference", task.reference_source)):
                with self.subTest(task=task_id, source=label), tempfile.TemporaryDirectory() as tmp:
                    directory = materialize(task_id, tmp)
                    (directory / "solution.py").write_text(source, encoding="utf-8")
                    proc = subprocess.run(
                        [sys.executable, "-B", "-m", "unittest", "test_public", "-v"],
                        cwd=directory, capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_workspace_excludes_evaluator_and_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = materialize("ttl_cache", tmp)
            self.assertEqual({p.name for p in directory.iterdir()}, {"TASK.md", "solution.py", "test_public.py"})
            self.assertEqual((directory / "solution.py").read_text(), TASKS["ttl_cache"].starting_source)

    def test_invalid_python_is_a_failed_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "solution.py"
            path.write_text("def broken(:\n", encoding="utf-8")
            result = evaluate("query_patch", path)
            self.assertFalse(result["task_pass"])
            self.assertEqual(result["passed"], 0)
            self.assertFalse(result["public_tests_pass"])
            self.assertIn("SyntaxError", result["public_tests_error"])
            self.assertTrue(all("SyntaxError" in check["error"] for check in result["checks"]))

    def test_hanging_candidate_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "solution.py"
            path.write_text("while True:\n    pass\n", encoding="utf-8")
            result = evaluate("query_patch", path, timeout=0.2)
            self.assertFalse(result["task_pass"])
            self.assertFalse(result["public_tests_pass"])
            self.assertIn("TimeoutExpired", result["public_tests_error"])
            self.assertTrue(all("TimeoutExpired" in check["error"] for check in result["checks"]))


if __name__ == "__main__":
    unittest.main()
