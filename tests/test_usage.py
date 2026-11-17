import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('usage', ROOT / 'scripts/compare_usage.py')
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)


def sample(mode, tokens):
    return dict(mode=mode, task_id='fixture-case', model='fixture-model', model_version='fixture-v1',
                fixture_sha256='0' * 64, settings={'effort': 'fixture'}, source='runtime_usage',
                passed=True, input_tokens=tokens, cached_input_tokens=0, output_tokens=20,
                reasoning_tokens=None, tool_calls=2, elapsed_seconds=3.5, attempts=1)


class UsageTests(unittest.TestCase):
    def test_synthetic_calculation_does_not_claim_measured_product_savings(self):
        result = usage.compare(sample('baseline', 100), sample('workflow', 75))
        self.assertEqual(result['input_tokens_reduction_percent'], 25)
        self.assertEqual(result['scope'], 'one_matched_pair_only')
        self.assertIsNone(result['money_saved'])

    def test_mismatched_model_task_or_snapshot_rejected(self):
        for field in ('model', 'model_version', 'fixture_sha256', 'task_id', 'settings'):
            b = sample('workflow', 75); b[field] = 'different'
            with self.subTest(field=field), self.assertRaises(ValueError):
                usage.compare(sample('baseline', 100), b)

    def test_failed_unmeasured_nonfinite_and_impossible_counts_rejected(self):
        for patch in ({'passed': False}, {'source': 'estimated'}, {'input_tokens': True},
                      {'elapsed_seconds': float('nan')}, {'cached_input_tokens': 999}, {'attempts': 2}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                usage.compare(sample('baseline', 100), sample('workflow', 75) | patch)


if __name__ == '__main__':
    unittest.main()
