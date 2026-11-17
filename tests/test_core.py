import importlib.util
from contextlib import closing
import json
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'skill/project-os/scripts/project_os.py'
spec = importlib.util.spec_from_file_location('project_os', SCRIPT)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workflow 中文 ')
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.state = core.initialize(self.root, 'Tiny Notes', 'Write small notes', 'zh')

    def payload(self, key='step-1', **changes):
        return dict(schema_version=1, project_id=self.state['project_id'],
                    expected_revision=self.state['revision'], idempotency_key=key,
                    agent='codex', summary='Added a note function', changes=changes)

    def test_init_is_idempotent_and_read_does_not_write(self):
        again = core.initialize(self.root, 'Other', 'Other', 'en')
        self.assertEqual(again, self.state)
        db = self.root / '.project-os/state.sqlite3'
        before = db.read_bytes()
        self.assertEqual(core.context(self.root)['project_id'], self.state['project_id'])
        self.assertEqual(db.read_bytes(), before)

    def test_new_agent_reads_saved_state_and_report_stays_unverified(self):
        p = self.payload(status='active', next_action='Test empty input')
        p['evidence'] = [{'kind': 'test', 'reference': 'python3 -m unittest', 'outcome': 'passed'}]
        receipt = core.record(self.root, p)
        view = core.context(self.root)
        self.assertEqual(receipt['outcome'], 'applied')
        self.assertEqual(view['fields']['next_action'], 'Test empty input')
        self.assertEqual(view['sources']['next_action']['kind'], 'agent_report')
        self.assertEqual(view['recent_records'][0]['agent'], 'codex')
        p2 = self.payload('claude-step', next_action='Document usage')
        p2.update(agent='claude-code', expected_revision=view['revision'])
        core.record(self.root, p2)
        self.assertEqual(core.context(self.root)['fields']['next_action'], 'Document usage')

    def test_same_key_replays_receipt_and_different_payload_is_rejected(self):
        p = self.payload(next_action='Test')
        first = core.record(self.root, p)
        self.assertEqual(core.record(self.root, p), first)
        self.assertEqual(len(core.history(self.root)['records']), 1)
        p['summary'] = 'different'
        with self.assertRaisesRegex(core.WorkflowError, 'idempotency_conflict'):
            core.record(self.root, p)

    def test_concurrent_writers_keep_stale_proposal(self):
        with ThreadPoolExecutor(2) as executor:
            results = list(executor.map(lambda p: core.record(self.root, p),
                           [self.payload('a', next_action='A'), self.payload('b', next_action='B')]))
        self.assertEqual(sorted(r['outcome'] for r in results), ['applied', 'stale'])
        self.assertEqual(core.context(self.root)['revision'], 1)
        self.assertEqual(len(core.history(self.root)['records']), 2)

    def test_manual_field_and_phase_group_are_protected(self):
        manual = self.payload('human', phase='Review', next_action='Keep this step')
        manual['agent'] = 'user'
        core.record(self.root, manual, manual=True)
        p = self.payload('agent', phase='Build', summary='Wrong phase', next_action='Overwrite')
        p['expected_revision'] = 1
        result = core.record(self.root, p)
        self.assertEqual(result['outcome'], 'protected')
        self.assertEqual(core.context(self.root)['fields']['next_action'], 'Keep this step')
        self.assertEqual(core.context(self.root)['fields']['summary'], '')

    def test_agent_cannot_confirm_project_complete_or_change_constraints(self):
        for change in [{'status': 'complete'}, {'constraints': []}, {'name': 'Changed'}]:
            with self.subTest(change=change), self.assertRaises(core.WorkflowError):
                core.record(self.root, self.payload(**change))
        self.assertEqual(core.context(self.root)['revision'], 0)

    def test_wrong_project_unknown_fields_and_false_revision_do_not_write(self):
        for patch in [{'project_id': 'wrong'}, {'surprise': 1}, {'expected_revision': True},
                      {'schema_version': 99}, {'agent': 'user'}, {'occurred_on': '2999-01-01'}]:
            with self.subTest(patch=patch), self.assertRaises(core.WorkflowError):
                core.record(self.root, self.payload() | patch)
        self.assertEqual(core.history(self.root)['records'], [])

    def test_context_bound_never_silently_omits_constraints(self):
        p = self.payload('manual', constraints=['不可丢失的约束' * 120] * 16)
        p['agent'] = 'user'
        core.record(self.root, p, manual=True)
        with self.assertRaisesRegex(core.WorkflowError, 'context_budget_exceeded'):
            core.context(self.root)
        large = core.context(self.root, 65536)
        self.assertEqual(large['fields']['constraints'], p['changes']['constraints'])
        self.assertLessEqual(len(core.encode(large).encode()) + 1, 65536)

    def test_no_accepted_state_can_exceed_maximum_context_capacity(self):
        p = self.payload('near-limit', constraints=['x' * 4096] * 15 + ['x' * 3300])
        p['agent'] = 'user'
        with self.assertRaisesRegex(core.WorkflowError, 'state_too_large'):
            core.record(self.root, p, manual=True)
        self.assertEqual(core.context(self.root)['revision'], 0)

    def test_killed_writer_recovers_without_publishing_partial_state(self):
        program = '''import sqlite3, sys
con=sqlite3.connect(sys.argv[1], isolation_level=None)
con.execute('PRAGMA cache_size=1')
con.execute('BEGIN IMMEDIATE')
con.execute('UPDATE project SET data=?', ('X'*40000,))
print('ready',flush=True)
sys.stdin.read()
'''
        proc = subprocess.Popen([sys.executable, '-c', program, str(self.root / '.project-os/state.sqlite3')],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), 'ready')
        finally:
            proc.kill()
            proc.communicate(timeout=5)
        self.assertEqual(core.context(self.root)['revision'], 0)
        self.assertEqual(core.history(self.root)['records'], [])

    def test_history_is_append_only_and_unknown_db_version_is_rejected(self):
        core.record(self.root, self.payload(next_action='Next'))
        db = self.root / '.project-os/state.sqlite3'
        with closing(sqlite3.connect(db)) as con, con:
            with self.assertRaises(sqlite3.DatabaseError):
                con.execute('DELETE FROM records')
            con.execute('PRAGMA user_version = 99')
        with self.assertRaisesRegex(core.WorkflowError, 'unsupported_schema'):
            core.context(self.root)

    def test_transaction_failure_rolls_back_state_and_record(self):
        db = self.root / '.project-os/state.sqlite3'
        with closing(sqlite3.connect(db)) as con, con:
            con.execute("CREATE TRIGGER injected_failure BEFORE INSERT ON records BEGIN SELECT RAISE(ABORT, 'fixture'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            core.record(self.root, self.payload(next_action='Must not survive'))
        self.assertEqual(core.context(self.root)['revision'], 0)
        self.assertEqual(core.history(self.root)['records'], [])

    def test_uninitialized_and_symlinked_storage_fail_without_touching_target(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            with self.assertRaisesRegex(core.WorkflowError, 'not_initialized'):
                core.context(root)
            (root / '.project-os').symlink_to(self.root / '.project-os', target_is_directory=True)
            with self.assertRaisesRegex(core.WorkflowError, 'unsafe_path'):
                core.context(root)

    def test_cli_returns_json_and_preserves_failed_input_file(self):
        f = self.root / 'report.json'
        f.write_text('{bad', encoding='utf-8')
        result = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.root),
                                 'record', '--input', str(f)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stderr)['error'], 'invalid_json')
        self.assertEqual(f.read_text(), '{bad')


if __name__ == '__main__':
    unittest.main()
