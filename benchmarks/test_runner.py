"""Checks for measurement logic; no model calls."""
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from benchmarks.run import parse_events, sanitize, schedule, run_workflow


class MeasurementTests(unittest.TestCase):
    def test_usage_includes_all_completed_stages_without_adding_reasoning_twice(self):
        result = parse_events('\n'.join([
            '{"type":"turn.completed","usage":{"input_tokens":100,"cached_input_tokens":60,"output_tokens":20,"reasoning_output_tokens":10}}',
            '{"type":"turn.completed","usage":{"input_tokens":40,"cached_input_tokens":0,"output_tokens":5,"reasoning_output_tokens":2}}',
        ]))
        self.assertEqual(result["usage"]["input_tokens"], 140)
        self.assertEqual(result["usage"]["cached_input_tokens"], 60)
        self.assertEqual(result["usage"]["output_tokens"], 25)

    def test_missing_usage_is_unknown(self):
        self.assertIsNone(parse_events('{"type":"turn.failed"}')["usage"])

    def test_balanced_paired_schedule(self):
        items = schedule(20261111, 3)
        self.assertEqual(len(items), 24)
        self.assertEqual(items, schedule(20261111, 3))
        first = []
        for left, right in zip(items[::2], items[1::2]):
            self.assertEqual((left["task_id"], left["repetition"]), (right["task_id"], right["repetition"]))
            self.assertEqual({left["condition"], right["condition"]}, {"single", "daisychain"})
            first.append(left["condition"])
        self.assertEqual(first.count("single"), 6)
        self.assertEqual(first.count("daisychain"), 6)

    def test_workspace_paths_are_redacted_including_resolved_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            self.assertEqual(sanitize(str(path / 'x'), path), '<RUN_WORKSPACE>/x')
            self.assertEqual(sanitize(str(path.resolve() / 'x'), path), '<RUN_WORKSPACE>/x')

    def test_deleted_or_binary_solution_is_recorded_without_regrade_or_crash(self):
        for binary in (False, True):
            with self.subTest(binary=binary), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                output = root / 'output'
                output.mkdir()
                args = SimpleNamespace(output=output, model='unused', timeout=480)

                def fake_stage(name, prompt, workspace, private, model, timeout, writable, catalog=None):
                    if name == 'implement':
                        if binary:
                            (workspace / 'solution.py').write_bytes(b'\xff\xfe')
                        else:
                            (workspace / 'solution.py').unlink()
                    return {'stage': name, 'completed': True, 'usage': {'input_tokens': 10,
                        'cached_input_tokens': 0, 'output_tokens': 2}, 'events': []}, 'done'

                item = {'task_id': 'ttl_cache', 'repetition': 1, 'condition': 'daisychain'}
                with patch('benchmarks.run.run_stage', side_effect=fake_stage):
                    result = run_workflow(item, 1, root / 'work', args, 'skill')
                self.assertFalse(result['workflow_completed'])
                self.assertTrue(result['scope_violation'])
                self.assertEqual(len(result['stages']), 3)
                self.assertEqual(result['usage']['input_tokens'], 30)
                self.assertTrue(result['usage_complete'])


if __name__ == '__main__':
    unittest.main()
