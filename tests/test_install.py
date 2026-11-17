import importlib.util
import pathlib
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('install', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workflow 安装 ')
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)

    def test_both_agents_get_identical_core_and_reinstall_is_noop(self):
        result = installer.install(self.root, 'both')
        self.assertEqual(result['status'], 'installed')
        for name in ('SKILL.md', 'scripts/project_os.py', 'references/protocol.md'):
            self.assertEqual((self.root / '.agents/skills/project-os' / name).read_bytes(),
                             (self.root / '.claude/skills/project-os' / name).read_bytes())
        self.assertEqual(installer.install(self.root, 'both')['status'], 'already_installed')
        self.assertFalse((self.root / 'AGENTS.md').exists())
        self.assertFalse((self.root / '.project-os/state.sqlite3').exists())

    def test_existing_skill_or_symlink_never_overwritten(self):
        path = self.root / '.agents/skills/project-os'
        path.mkdir(parents=True)
        (path / 'SKILL.md').write_text('user content')
        with self.assertRaises(installer.InstallError):
            installer.install(self.root, 'both')
        self.assertEqual((path / 'SKILL.md').read_text(), 'user content')
        self.assertFalse((self.root / '.claude').exists())
        with tempfile.TemporaryDirectory() as other:
            (self.root / '.claude').symlink_to(other, target_is_directory=True)
            with self.assertRaises(installer.InstallError):
                installer.install(self.root, 'claude')
            self.assertEqual(list(pathlib.Path(other).iterdir()), [])

    def test_uninstall_retains_database_edits_and_unowned_files(self):
        installer.install(self.root, 'both')
        db = self.root / '.project-os/state.sqlite3'
        db.write_bytes(b'fixture state retained')
        changed = self.root / '.agents/skills/project-os/SKILL.md'
        changed.write_text('user edit')
        extra = changed.parent / 'my-notes.md'
        extra.write_text('keep')
        result = installer.uninstall(self.root, 'both')
        self.assertIn(str(changed.relative_to(self.root)), result['preserved'])
        self.assertEqual(db.read_bytes(), b'fixture state retained')
        self.assertEqual(changed.read_text(), 'user edit')
        self.assertTrue(extra.exists())
        self.assertFalse((self.root / '.claude/skills/project-os').exists())

    def test_manifest_cannot_delete_outside_skill(self):
        import json
        installer.install(self.root, 'codex')
        outside = self.root / 'keep.txt'
        outside.write_text('keep')
        manifest = self.root / '.project-os/installation.json'
        data = json.loads(manifest.read_text())
        data['files']['keep.txt'] = installer.digest(outside.read_bytes())
        manifest.write_text(json.dumps(data))
        with self.assertRaises(installer.InstallError):
            installer.uninstall(self.root, 'codex')
        self.assertEqual(outside.read_text(), 'keep')

    def test_interrupted_install_rolls_back_its_own_files(self):
        original = installer.create_file
        calls = 0
        def broken(path, body):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('fixture interruption')
            return original(path, body)
        with patch.object(installer, 'create_file', broken), self.assertRaises(OSError):
            installer.install(self.root, 'both')
        self.assertFalse((self.root / '.agents/skills/project-os').exists())

    def test_racing_user_file_is_never_removed_by_rollback(self):
        original = installer.create_file
        def race(path, body):
            path.write_text('Concurrent user content')
            return original(path, body)
        with patch.object(installer, 'create_file', race), self.assertRaises(FileExistsError):
            installer.install(self.root, 'codex')
        raced = self.root / '.agents/skills/project-os/SKILL.md'
        self.assertEqual(raced.read_text(), 'Concurrent user content')


if __name__ == '__main__':
    unittest.main()
