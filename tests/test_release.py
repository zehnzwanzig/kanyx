"""Release metadata and repository sanity checks."""
import unittest
from pathlib import Path
from version import __version__

ROOT = Path(__file__).resolve().parents[1]

class ReleaseTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(__version__, '1.0.1')

    def test_release_files(self):
        for path in ['LICENSE', 'CHANGELOG.md', 'SECURITY.md',
                     'CONTRIBUTING.md', '.gitignore', '.github/workflows/ci.yml',
                     '.github/workflows/release.yml', 'assets/kanyx.ico',
                     'assets/kanyx.png']:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())

    def test_legacy_database_preservation(self):
        from db import Store
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = Store(root)
            a.add_board('Saved board')
            a.close()
            original = root / 'data/kanyx.db'
            old_name = root / 'data/pyban.db'
            original.rename(old_name)
            b = Store(root)
            self.assertEqual(b.dbfile.name, 'pyban.db')
            self.assertTrue(any(x['title'] == 'Saved board' for x in b.rows('SELECT title FROM boards')))
            b.close()
