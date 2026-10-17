import tempfile
import unittest
from pathlib import Path
from scripts.prepare_runtime_notices import git_blob_sha, describe_native_files, is_native_library


class TestRuntimeNotices(unittest.TestCase):
    def test_git_blob_sha(self):
        self.assertEqual(git_blob_sha(b'test'), '30d74d258442c7c65512eafab474568dd706c430')

    def test_native_suffixes(self):
        self.assertTrue(is_native_library('libQt6Core.so.6'))
        self.assertTrue(is_native_library('Qt6Widgets.dll'))
        self.assertTrue(is_native_library('QtCore.pyd'))
        self.assertFalse(is_native_library('README.md'))

    def test_inventory_classification(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in ('_internal/PySide6/Qt6Core.dll', '_internal/libssl-3-x64.dll',
                         '_internal/python312.dll', '_internal/something.unknown'):
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b'123')
            got = describe_native_files(root)
            self.assertEqual([x['group'] for x in got], ['Qt/Qt-plugin', 'OpenSSL', 'CPython/runtime-extension'])


if __name__ == '__main__':
    unittest.main()
