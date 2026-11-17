import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release', ROOT / 'scripts/export_release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_allowlist_excludes_runtime_private_and_git_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); source = base / 'source'; source.mkdir()
            (source / 'README.md').write_text('Public fixture')
            (source / 'release-files.txt').write_text('README.md\n')
            (source / '.env').write_text('PRIVATE_FIXTURE')
            (source / '.project-os').mkdir()
            (source / '.project-os/state.sqlite3').write_bytes(b'PRIVATE_FIXTURE')
            output = base / 'export'
            receipt = release.export(source, output)
            self.assertEqual(receipt['files'], 1)
            self.assertEqual(sorted(p.name for p in output.iterdir()), ['README.md', 'SHA256SUMS'])
            self.assertFalse((output / '.git').exists())

    def test_traversal_symlink_and_private_content_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); source = base / 'source'; source.mkdir()
            outside = base / 'private'; outside.write_text('outside')
            allow = source / 'release-files.txt'
            allow.write_text('../private\n')
            with self.assertRaises(ValueError):
                release.export(source, base / 'out1')
            allow.write_text('public.md\n')
            (source / 'public.md').symlink_to(outside)
            with self.assertRaises(ValueError):
                release.export(source, base / 'out2')
            (source / 'public.md').unlink()
            (source / 'public.md').write_text('-----BEGIN ' + 'PRIVATE KEY-----')
            with self.assertRaises(ValueError):
                release.export(source, base / 'out3')

    def test_export_never_overwrites_an_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); target = base / 'release'; target.mkdir()
            (target / 'keep').write_text('keep')
            with self.assertRaises(FileExistsError):
                release.export(ROOT, target)
            self.assertEqual((target / 'keep').read_text(), 'keep')

    def test_offline_demo_reaches_revision_two_without_model_calls(self):
        run = subprocess.run([sys.executable, str(ROOT / 'examples/demo.py')], capture_output=True, text=True, check=True)
        result = json.loads(run.stdout)
        self.assertEqual(result['model_calls'], 0)
        self.assertIsNone(result['actual_model_tokens'])
        self.assertEqual(result['final_revision'], 2)
        self.assertEqual(len(result['frames']), 6)
        self.assertNotIn('project_id', run.stdout)

    def test_canary_preparation_does_not_execute_the_task_or_launch_agents(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'fixture'
            run = subprocess.run([sys.executable, str(ROOT / 'scripts/prepare_canary.py'), '--output', str(target)],
                                 capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(run.stdout)['sessions_launched'], 0)
            self.assertEqual(len(list((target / 'canary-prompts').glob('*.txt'))), 4)
            tests = subprocess.run([sys.executable, '-m', 'unittest'], cwd=target, capture_output=True)
            self.assertNotEqual(tests.returncode, 0)  # Task is intentionally not implemented.


if __name__ == '__main__':
    unittest.main()
