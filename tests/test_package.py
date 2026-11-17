import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_package', ROOT / 'scripts/check_package.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class PackageTests(unittest.TestCase):
    def fixture(self, root):
        skill = root / 'skill/project-os'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('---\nname: project-os\ndescription: Resume this local project and save its progress.\n---\n# Workflow\n')
        (root / 'README.md').write_text('[Skill](skill/project-os/SKILL.md)\n')
        (root / 'release-files.txt').write_text('README.md\nskill/project-os/SKILL.md\n')

    def test_valid_small_package_checks_without_runtime_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.fixture(root)
            result = checker.check(root)
            self.assertEqual(result['status'], 'passed')
            self.assertEqual(result['files'], 2)

    def test_broken_relative_link_blocks_a_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.fixture(root)
            (root / 'README.md').write_text('[Missing](missing.md)\n')
            with self.assertRaisesRegex(ValueError, 'Missing local link'):
                checker.check(root)

    def test_missing_skill_metadata_and_stale_checksums_are_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.fixture(root)
            (root / 'SHA256SUMS').write_text('0' * 64 + '  README.md\n')
            with self.assertRaisesRegex(ValueError, 'checksums'):
                checker.check(root)
            (root / 'SHA256SUMS').unlink()
            skill = root / 'skill/project-os/SKILL.md'
            skill.write_text('---\nname: project-os\n---\n# Workflow\n')
            with self.assertRaisesRegex(ValueError, 'metadata'):
                checker.check(root)


if __name__ == '__main__':
    unittest.main()
