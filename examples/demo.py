#!/usr/bin/env python3
"""Offline executable demonstration. No Codex/Claude sessions or model calls."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

PACKAGE = Path(__file__).resolve().parents[1]


def run_demo():
    frames = []
    with tempfile.TemporaryDirectory(prefix='workflow-demo-') as temp:
        root = Path(temp)
        def run(title, args, show):
            started = time.monotonic()
            result = subprocess.run([sys.executable, *args], cwd=root, text=True, capture_output=True, check=True)
            data = json.loads(result.stdout)
            frames.append({'title': title, 'result': show(data),
                           'elapsed_seconds': round(time.monotonic() - started, 4)})
            return data
        run('1. Install the same Skill for both agents',
            [str(PACKAGE / 'install.py'), 'install', '--project', '.', '--agent', 'both'],
            lambda d: {'status': d['status'], 'files_written': d['files_written']})
        codex = '.agents/skills/project-os/scripts/project_os.py'
        claude = '.claude/skills/project-os/scripts/project_os.py'
        state = run('2. Initialize Tiny Notes', [codex, '--project', '.', 'init', '--name', 'Tiny Notes',
                    '--purpose', 'Save small local notes', '--language', 'en'],
                    lambda d: {'name': d['fields']['name'], 'revision': d['revision']})
        (root / 'notes.py').write_text('def normalize(text):\n    return text.strip()\n')
        p = dict(schema_version=1, project_id=state['project_id'], expected_revision=0,
                 idempotency_key='demo-first', agent='fixture-codex', summary='Added whitespace normalization.',
                 changes={'status': 'active', 'summary': 'Normalization implemented.', 'next_action': 'Reject empty notes.'},
                 evidence=[{'kind': 'file', 'reference': 'notes.py', 'outcome': 'observed'}])
        report = root / '.project-os/report.json'
        report.write_text(json.dumps(p))
        run('3. Save a Codex-shaped fixture report', [codex, '--project', '.', 'record', '--input', str(report)],
            lambda d: {'outcome': d['outcome'], 'revision': d['revision_after'], 'evidence': d['evidence_status']})
        next_state = run('4. Read through the Claude Code installation', [claude, '--project', '.', 'context'],
                         lambda d: {'revision': d['revision'], 'next_action': d['fields']['next_action']})
        assert next_state['fields']['next_action'] == 'Reject empty notes.'
        (root / 'notes.py').write_text('def normalize(text):\n    value = text.strip()\n    if not value:\n        raise ValueError("Empty note")\n    return value\n')
        verified = subprocess.run([sys.executable, '-c', 'from notes import normalize; assert normalize(" hello ") == "hello"\ntry:\n normalize(" ")\nexcept ValueError:\n pass\nelse:\n raise AssertionError("empty note accepted")'], cwd=root, capture_output=True)
        assert verified.returncode == 0
        p.update(expected_revision=next_state['revision'], idempotency_key='demo-second', agent='fixture-claude-code',
                 summary='Empty input now rejected; local behavior checks passed.',
                 changes={'summary': 'Normalization and empty input checks implemented.', 'next_action': 'Document usage.'},
                 evidence=[{'kind': 'test', 'reference': 'examples/demo.py behavior assertions', 'outcome': 'passed'}])
        report.write_text(json.dumps(p))
        run('5. Save the next fixture result', [claude, '--project', '.', 'record', '--input', str(report)],
            lambda d: {'outcome': d['outcome'], 'revision': d['revision_after']})
        final = run('6. A fresh helper process reads the latest step', [codex, '--project', '.', 'context'],
                    lambda d: {'revision': d['revision'], 'status': d['fields']['status'], 'next_action': d['fields']['next_action']})
        assert final['revision'] == 2 and final['fields']['status'] == 'active'
    return {'mode': 'offline_fixture_not_live_agents', 'model_calls': 0, 'frames': frames,
            'final_revision': final['revision'], 'context_bytes': len(json.dumps(final, ensure_ascii=False, separators=(',', ':')).encode()) + 1,
            'actual_model_tokens': None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional sanitized demo record; never contains project paths or IDs')
    args = parser.parse_args()
    result = run_demo()
    body = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        with args.output.open('x') as out:
            out.write(body)
    print(body, end='')
