import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.prepare_qt_third_party_notices import (
    Attribution, NOTICES, git_blob_sha, source_url, verified_source, write_notices,
)


class ThirdPartyNoticeTests(unittest.TestCase):
    def test_blob_hash_matches_git(self):
        self.assertEqual(git_blob_sha(b'test'), '30d74d258442c7c65512eafab474568dd706c430')

    def test_immutable_source_url(self):
        self.assertEqual(source_url(NOTICES[0]),
                         'https://raw.githubusercontent.com/qt/qtimageformats/v6.12.0/src/3rdparty/libtiff/COPYRIGHT')

    def test_rejects_modified_offline_notice(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / NOTICES[0].filename).write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'Invalid cached'):
                verified_source(NOTICES[0], cache_dir=p)

    def test_write_licenses_and_manifest_without_network(self):
        blob = b'license data from pinned source\n'
        a = Attribution('test-LICENSE.txt', 'qt/qtbase', 'path/LICENSE',
                        git_blob_sha(blob), 'Test lib', 'unit test')
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cache = base / 'cache'
            cache.mkdir()
            (cache / a.filename).write_bytes(blob)
            dest = base / 'bundle'
            dest.mkdir()
            with patch('scripts.prepare_qt_third_party_notices.NOTICES', (a,)):
                result = write_notices(dest, cache)
            self.assertEqual(len(result['notices']), 1)
            self.assertEqual((dest / 'licenses/third-party/test-LICENSE.txt').read_bytes(), blob)
            self.assertIn('NOT_LEGAL_CLEARANCE', (dest / 'THIRD_PARTY_QT_MANIFEST.json').read_text())
            self.assertTrue((dest / 'THIRD_PARTY_QT_NOTICES.md').is_file())


if __name__ == '__main__':
    unittest.main()
