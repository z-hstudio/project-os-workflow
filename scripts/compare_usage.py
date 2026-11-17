#!/usr/bin/env python3
"""Compare two user-supplied, matched runtime measurements. Makes no model calls."""
import argparse
import json
import math
from pathlib import Path


def compare(baseline, workflow):
    identities = ('task_id', 'model', 'model_version', 'fixture_sha256', 'settings')
    for key in identities:
        if key not in baseline or key not in workflow or baseline[key] != workflow[key]:
            raise ValueError('Comparison requires matching ' + key)
    for entry, mode in ((baseline, 'baseline'), (workflow, 'workflow')):
        if entry.get('mode') != mode or entry.get('source') != 'runtime_usage' or entry.get('passed') is not True:
            raise ValueError('Both cases must pass and use actual runtime usage, not estimates')
        if type(entry.get('attempts')) is not int or entry['attempts'] != 1:
            raise ValueError('This bounded benchmark requires exactly one attempt per case')
        for key in ('input_tokens', 'output_tokens', 'tool_calls'):
            if type(entry.get(key)) is not int or entry[key] < 0:
                raise ValueError('Invalid count: ' + key)
        for key, total in (('cached_input_tokens', 'input_tokens'), ('reasoning_tokens', 'output_tokens')):
            value = entry.get(key)
            if value is not None and (type(value) is not int or not 0 <= value <= entry[total]):
                raise ValueError('Invalid subset count: ' + key)
        seconds = entry.get('elapsed_seconds')
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Invalid elapsed_seconds')
    before, after = baseline['input_tokens'], workflow['input_tokens']
    return {'scope': 'one_matched_pair_only', 'input_tokens_reduction': before - after,
            'input_tokens_reduction_percent': round(100 * (before - after) / before, 2) if before else None,
            'output_tokens_difference': workflow['output_tokens'] - baseline['output_tokens'],
            'baseline': baseline, 'workflow': workflow, 'money_saved': None,
            'note': 'No cost or general effectiveness claim. Cached/reasoning tokens are subsets, not added twice.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--workflow', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compare(json.loads(args.baseline.read_text()), json.loads(args.workflow.read_text())),
                     ensure_ascii=False, indent=2))
