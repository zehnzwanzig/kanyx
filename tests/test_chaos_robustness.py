"""Kanyx chaos/robustness regression tests. NEVER uses your actual workspace.

Run: python -m unittest discover -s tests -p 'test_chaos*.py' -v
Optional: KANYX_CHAOS_ITERATIONS=1000; KANYX_CHAOS_BIG_MB=32
UI tests run offscreen if PySide6 is installed; never launch native files.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sqlite3
import stat
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

from db import Store
from portability import export_workspace, stage_import, swap_in_workspace
import portability

# Reproducible even if a different Python version or computer runs the suite.
SEED = int(os.environ.get('KANYX_CHAOS_SEED', '12648430'))  # 0xC0FFEE
ITERATIONS = min(10000, max(10, int(os.environ.get('KANYX_CHAOS_ITERATIONS', '200'))))
LARGE_MB = min(64, max(1, int(os.environ.get('KANYX_CHAOS_BIG_MB', '8'))))

STRANGE_TEXTS = [
    'Plain ASCII', 'äöü ß ñ à é č ğ ı ł œ', 'NFC café', 'NFD cafe\u0301',
    'العربية مرحبا بالعالم', 'עברית שלום עולם', 'فارسی سلام', 'हिन्दी नमस्ते',
    'தமிழ் வணக்கம்', 'ภาษาไทย', 'ខ្មែរ', '中文简体 繁體中文', '日本語 カタカナ',
    '한국어 안녕하세요', 'ქართული', 'Ελληνικά', 'Кириллица Привет',
    '😀🔥🎉🚀👨\u200d👩\u200d👧\u200d👦🏳️\u200d🌈🇦🇹🇯🇵',
    '𝔘𝔫𝔦𝔠𝔬𝔡𝔢 𝑥² 𝕏 ∑ ∞ √ ∫', 'a\u0301\u0301\u0301\u0301\u0301',
    '\u200b\u200c\u200d word \ufeff', '\u202eRTL override\u202c / LTR',
    'new\nline\rCR\ttab', '\x00 NUL \x01 STX \x1b ESC \x7f DEL',
    '"single\'quote" `code` \\ slash / : ; ,',
    '<script>alert(1)</script> &amp; <b>markup</b>',
    'SELECT * FROM cards; DROP TABLE cards; --', "' OR 1=1 --",
    '# Markdown **bold** [link](file:///C:/bad) ![image](https://invalid.example/a.png)',
    '${HOME} %APPDATA% %s {0} {{template}}',
    '../..\\..\\windows\\system32/', 'C:\\path\\to\\file',
    ' % _ [ ] * ? # @ ! 🦊 ',
    'A' * 4096, '字' * 4096,
]
RANDOM_ALPHABET = (
    'abcXYZ0123456789 -_\\/.,:;[](){}!%&=+\'"`\n\t' +
    'äñ日界本語漢한글العربيةעבריתहिन्दी' +
    '😀🧪💾🔥🚀\u200d\u0301\u200f\u200e'
)


def temporary_file(folder: Path, name: str, payload: bytes = b'') -> Path:
    path = folder / name
    path.write_bytes(payload)
    return path


class IsolatedStore(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kanyx-chaos-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'sandbox')
        self.addCleanup(self.store.close)
        self.board_id = self.store.rows('SELECT id FROM boards ORDER BY id LIMIT 1')[0]['id']
        self.lane_id = self.store.rows('SELECT id FROM lanes WHERE board_id=? ORDER BY position,id', (self.board_id,))[0]['id']
        self.card_id = self.store.add_card(self.lane_id, 'CHAOS CARD')

    def assert_db_ok(self):
        self.assertEqual(self.store.con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertIsNone(self.store.con.execute('PRAGMA foreign_key_check').fetchone())


class UnicodeAndFuzzTests(IsolatedStore):
    def test_mixed_writing_systems_escapes_emoji_html_sql_and_controls_roundtrip(self):
        """Every text is saved, reread through SQLite and checked for byte-identical Unicode."""
        for index, phrase in enumerate(STRANGE_TEXTS):
            with self.subTest(case=index, sample=repr(phrase[:36])):
                self.store.update_card(self.card_id, phrase, phrase + '\n' + phrase,
                                       'Normal', '', 'tag' + str(index), [(phrase, True)])
                card = self.store.card(self.card_id)
                self.assertEqual(card['title'], phrase)
                self.assertEqual(card['description'], phrase + '\n' + phrase)
                self.assertEqual(self.store.card_checks(self.card_id)[0]['body'], phrase.strip())
                self.assertIn('tag' + str(index), self.store.card_tags(self.card_id))
        self.assert_db_ok()

    def test_deterministic_random_unicode_fuzz(self):
        rng = random.Random(SEED)
        for i in range(ITERATIONS):
            phrase = ''.join(rng.choice(RANDOM_ALPHABET) for _ in range(rng.randrange(1, 180)))
            desc = phrase[::-1] + '\n' + phrase
            with self.subTest(iteration=i, seed=SEED):
                self.store.update_card(self.card_id, phrase, desc, 'Hoch', '', '', [])
                self.assertEqual(self.store.card(self.card_id)['description'], desc)
                self.assertEqual(self.store.card(self.card_id)['title'], phrase)
        self.assert_db_ok()

    def test_long_title_description_and_checklist(self):
        title = '𐍈🦄' * 3500
        description = ('# Header\n\x00 🇦🇹 العربية 日本語 <div>\n' * 2800)
        self.store.update_card(self.card_id, title, description, 'Normal', '',
                               'longtag,🦊', [('✓' * 2000, False)])
        self.assertEqual(self.store.card(self.card_id)['title'], title)
        self.assertEqual(self.store.card(self.card_id)['description'], description)
        self.assertEqual(self.store.card_checks(self.card_id)[0]['body'], '✓' * 2000)
        self.assert_db_ok()

    def test_injection_like_strings_are_only_data(self):
        payload = "'); DELETE FROM boards; DROP TABLE cards; --"
        self.store.rename_board(self.board_id, payload)
        self.store.update_card(self.card_id, payload, payload, 'Normal', '', payload, [])
        matches = self.store.search_cards(self.board_id, payload)
        self.assertEqual([r['id'] for r in matches], [self.card_id])
        self.assertEqual(self.store.one('SELECT title FROM boards WHERE id=?', (self.board_id,))['title'], payload)
        self.assert_db_ok()

    def test_unicode_renaming_reopen_and_search(self):
        unique = 'قائمة 😺 日本語 end'
        self.store.rename_board(self.board_id, unique)
        self.store.rename_lane(self.lane_id, '🧪🧬 RTL مرحبا')
        self.store.update_card(self.card_id, 'Notes ' + unique, unique, 'Normal', '', 'unique🧬', [])
        self.store.close()
        self.store = Store(self.root / 'sandbox')
        self.addCleanup(self.store.close)
        self.assertEqual(self.store.one('SELECT title FROM boards WHERE id=?', (self.board_id,))['title'], unique)
        self.assertEqual(self.store.one('SELECT title FROM lanes WHERE id=?', (self.lane_id,))['title'], '🧪🧬 RTL مرحبا')
        self.assertEqual([r['id'] for r in self.store.search_cards(self.board_id, 'قائمة')], [self.card_id])
        self.assert_db_ok()

    def test_tricky_tag_list_and_checklist_whitespace(self):
        self.store.update_card(self.card_id, 'tag test', '', 'Normal', '',
                               ' blue, 日本語 , 🙃, ,  ,\t',
                               [('  item one  ', True), ('\n\t', True), ('إجراء 😀', False)])
        tags = self.store.card_tags(self.card_id)
        self.assertEqual(len(tags), len(set(t.casefold() for t in tags)))
        self.assertIn('日本語', tags)
        self.assertIn('🙃', tags)
        checks = self.store.card_checks(self.card_id)
        self.assertEqual([r['body'] for r in checks], ['item one', 'إجراء 😀'])
        self.assert_db_ok()

    def test_case_insensitive_duplicate_tags_must_not_break_save_regression(self):
        """Regression: case-insensitive repeated tags must be deduplicated."""
        self.store.update_card(self.card_id, 'duplicates', '', 'Normal', '',
                               'blue, BLUE, blue', [])
        self.assertEqual(len(self.store.card_tags(self.card_id)), 1)
        self.assert_db_ok()

    def test_bad_card_color_does_not_corrupt_previous_values(self):
        self.store.update_card(self.card_id, 'before', 'before', 'Normal', '', '', [])
        with self.assertRaises(ValueError):
            self.store.update_card(self.card_id, 'after', 'after', 'Normal', '', '', [], '#not-a-color')
        self.assertEqual(self.store.card(self.card_id)['title'], 'before')
        self.assert_db_ok()

    def test_invalid_unpaired_surrogates_are_rejected_without_database_damage(self):
        """Invalid Unicode must not destroy the database (GUI-level handling is separate)."""
        before = self.store.card(self.card_id)['title']
        for invalid in ('bad\ud800', '\udfff', 'high\ud800low'):
            with self.subTest(value=repr(invalid)):
                with self.assertRaises((UnicodeError, sqlite3.Error, ValueError)):
                    self.store.update_card(self.card_id, invalid, '', 'Normal', '', '', [])
                self.assertEqual(self.store.card(self.card_id)['title'], before)
        self.assert_db_ok()

    def test_search_percent_and_underscore_are_literal_not_wildcards_regression(self):
        """Regression: LIKE wildcards must be escaped in user search input."""
        self.store.update_card(self.card_id, 'ordinary title', '', 'Normal', '', '', [])
        self.assertEqual(self.store.search_cards(self.board_id, '%'), [])
        self.assertEqual(self.store.search_cards(self.board_id, '_'), [])


class AttachmentChaosTests(IsolatedStore):
    def test_file_extension_filename_unicode_and_binary_matrix(self):
        names = [
            'normal.txt', 'data', '.env', '.txt', 'archive.tar.gz', 'UPPER.JPEG',
            'test.json', 'binary.exe', 'unusual.💾', 'emoji🔥.png',
            'العربية.pdf', '日本語画像.webp', '😀🐉.zip', 'quote\'s.txt',
            'space in file name.csv', 'comma;percent%_dash-.svg', 'δοκιμή.xml',
            'мир.docx', 'music🎵.mp3', 'zero.log',
        ]
        for i, name in enumerate(names):
            payload = (name + '\n').encode('utf8') + bytes(range(256)) + b'\x00\xff' + bytes([i])
            with self.subTest(name=name):
                src = temporary_file(self.root, name, payload)
                file_id = self.store.add_file(self.card_id, src)
                row = self.store.one('SELECT * FROM files WHERE id=?', (file_id,))
                self.assertEqual(row['original_name'], name)
                self.assertNotIn('/', row['stored_name'])
                self.assertNotIn('\\', row['stored_name'])
                self.assertEqual((self.store.attachments / row['stored_name']).read_bytes(), payload)
                self.store.delete_file(file_id)
                self.assertFalse((self.store.attachments / row['stored_name']).exists())
        self.assertEqual(self.store.card_files(self.card_id), [])
        self.assertEqual(self.store.verify_integrity(), [])
        self.assert_db_ok()

    def test_same_filename_twice_generates_independent_storage_paths(self):
        src1 = self.root / 'one'
        src2 = self.root / 'two'
        src1.mkdir()
        src2.mkdir()
        first = temporary_file(src1, 'same.txt', b'first')
        second = temporary_file(src2, 'same.txt', b'second')
        id1 = self.store.add_file(self.card_id, first)
        id2 = self.store.add_file(self.card_id, second)
        r1 = self.store.one('SELECT * FROM files WHERE id=?', (id1,))
        r2 = self.store.one('SELECT * FROM files WHERE id=?', (id2,))
        self.assertEqual(r1['original_name'], r2['original_name'])
        self.assertNotEqual(r1['stored_name'], r2['stored_name'])
        self.assertEqual((self.store.attachments / r1['stored_name']).read_bytes(), b'first')
        self.assertEqual((self.store.attachments / r2['stored_name']).read_bytes(), b'second')
        self.store.delete_file(id1)
        self.assertEqual((self.store.attachments / r2['stored_name']).read_bytes(), b'second')
        self.assertEqual(self.store.verify_integrity(), [])

    def test_corrupt_db_stored_name_must_not_delete_outside_attachments_regression(self):
        """Regression: tampered stored_name must never allow path traversal."""
        src = temporary_file(self.root, 'regular.txt', b'initial')
        fid = self.store.add_file(self.card_id, src)
        protected = temporary_file(self.store.data, 'important-outside-attachments.txt', b'DO NOT DELETE')
        self.store.execute('UPDATE files SET stored_name=? WHERE id=?',
                           ('../important-outside-attachments.txt', fid))
        self.store.delete_file(fid)
        self.assertIsNone(self.store.one("SELECT id FROM files WHERE id=?", (fid,)))
        self.assertTrue(protected.is_file())
        self.assertEqual(protected.read_bytes(), b'DO NOT DELETE')

    def test_zero_byte_file_roundtrips_into_workspace_archive(self):
        empty = temporary_file(self.root, 'empty.bin', b'')
        fid = self.store.add_file(self.card_id, empty)
        row = self.store.one('SELECT * FROM files WHERE id=?', (fid,))
        self.assertEqual((self.store.attachments / row['stored_name']).stat().st_size, 0)
        archive = export_workspace(self.store, self.root / 'empty.kanyx')
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(z.read('attachments/' + row['stored_name']), b'')
        self.assertEqual(self.store.verify_integrity(), [])

    def test_large_binary_file_hashes_and_portable_export(self):
        src = self.root / 'large-📦-file.without-a-normal-extension'
        block = hashlib.sha256(b'Kanyx deterministic chaos blob').digest() * 32768  # 1 MiB
        with src.open('wb') as stream:
            for _ in range(LARGE_MB):
                stream.write(block)
        fid = self.store.add_file(self.card_id, src)
        row = self.store.one('SELECT * FROM files WHERE id=?', (fid,))
        stored = self.store.attachments / row['stored_name']
        self.assertEqual(stored.stat().st_size, LARGE_MB * 1024 * 1024)
        self.assertEqual(portability._sha256(src), portability._sha256(stored))
        exported = export_workspace(self.store, self.root / 'large.kanyx')
        with zipfile.ZipFile(exported) as z:
            self.assertEqual(z.getinfo('attachments/' + row['stored_name']).file_size, LARGE_MB * 1024 * 1024)

    def test_missing_source_on_save_does_not_create_record(self):
        missing = self.root / 'selected-but-removed.txt'
        with self.assertRaises(OSError):
            self.store.add_file(self.card_id, missing)
        self.assertEqual(self.store.card_files(self.card_id), [])
        self.assertEqual(self.store.verify_integrity(), [])

    def test_directory_disguised_as_attachment_cannot_be_saved(self):
        directory = self.root / 'looks-like-a-file.png'
        directory.mkdir()
        with self.assertRaises(OSError):
            self.store.add_file(self.card_id, directory)
        self.assertEqual(self.store.card_files(self.card_id), [])

    def test_missing_saved_file_detected_export_refused_and_delete_survives(self):
        """A manually deleted attachment leaves a DB record; opening tested below."""
        src = temporary_file(self.root, 'deleted-later.pdf', b'%PDF-1.0\n not really a PDF')
        fid = self.store.add_file(self.card_id, src)
        row = self.store.one('SELECT * FROM files WHERE id=?', (fid,))
        stored = self.store.attachments / row['stored_name']
        stored.unlink()  # Emulate deleting the attachment behind Kanyx's back.
        self.assertIn(row['stored_name'], self.store.verify_integrity())
        with self.assertRaisesRegex(ValueError, 'Missing or unsafe attachment'):
            export_workspace(self.store, self.root / 'corrupt-workspace.kanyx')
        self.assertFalse((self.root / 'corrupt-workspace.kanyx').exists())
        self.store.delete_file(fid)  # Must work even if file is already gone.
        self.assertEqual(self.store.verify_integrity(), [])
        self.assertEqual(self.store.card_files(self.card_id), [])
        self.assertIsNotNone(self.store.card(self.card_id))

    def test_copy_failure_creates_neither_db_entry_nor_file(self):
        src = temporary_file(self.root, 'locked.txt', b'still here')
        with patch('db.shutil.copy2', side_effect=PermissionError('simulated locked file')):
            with self.assertRaises(PermissionError):
                self.store.add_file(self.card_id, src)
        self.assertEqual(self.store.card_files(self.card_id), [])
        self.assertFalse(any(self.store.attachments.iterdir()))
        self.assert_db_ok()

    def test_delete_duplicate_and_archive_with_files(self):
        src = temporary_file(self.root, '🔐data', b'one two three\x00')
        self.store.add_file(self.card_id, src)
        copy_id = self.store.duplicate_card(self.card_id)
        originals = self.store.card_files(self.card_id)
        copies = self.store.card_files(copy_id)
        self.assertEqual(len(originals), 1)
        self.assertEqual(len(copies), 1)
        self.assertNotEqual(originals[0]['stored_name'], copies[0]['stored_name'])
        self.store.archive_card(self.card_id)
        self.assertTrue(self.store.card(self.card_id)['archived_at'])
        self.store.delete_card(self.card_id)
        self.assertTrue((self.store.attachments / copies[0]['stored_name']).is_file())
        self.store.delete_card(copy_id)
        self.assertEqual(list(self.store.attachments.iterdir()), [])
        self.assert_db_ok()

    def test_bulk_attach_delete_cycles_no_orphans(self):
        for iteration in range(40):
            content = bytes([iteration]) * (1 + iteration * 37)
            src = temporary_file(self.root, 'iter-' + str(iteration) + '.bin', content)
            fid = self.store.add_file(self.card_id, src)
            self.store.delete_file(fid)
        self.assertEqual(self.store.card_files(self.card_id), [])
        self.assertEqual(list(self.store.attachments.iterdir()), [])
        self.assert_db_ok()


class RandomizedBoardMovementTests(IsolatedStore):
    def test_repeated_move_reorder_archive_restore_and_integrity(self):
        rng = random.Random(SEED + 7)
        extra_lanes = [self.store.add_lane(self.board_id, 'Chaos ' + str(i)) for i in range(4)]
        lane_ids = [self.lane_id] + extra_lanes
        cards = [self.store.add_card(rng.choice(lane_ids), 'card ' + str(i)) for i in range(40)]
        for iteration in range(160):
            cid = rng.choice(cards)
            self.store.move_card(cid, rng.choice(lane_ids), rng.randrange(0, 100))
            if iteration % 5 == 0:
                self.store.move_lane(rng.choice(lane_ids), rng.randrange(-2, 100))
            if iteration % 11 == 0:
                self.store.archive_card(cid, True)
                self.store.archive_card(cid, False)
        self.assertEqual(len(self.store.rows('SELECT id FROM cards')), 1 + len(cards))
        for cid in cards:
            self.assertIsNotNone(self.store.card(cid))
        self.assertEqual(self.store.verify_integrity(), [])
        self.assert_db_ok()


class WorkspaceAttackTests(IsolatedStore):
    def valid_archive(self):
        self.store.update_card(self.card_id, 'Keep me 😀', 'متنِ عربي', 'Normal', '', '', [])
        return export_workspace(self.store, self.root / 'valid.kanyx')

    def assert_rejected_safely(self, path, errors=(ValueError, zipfile.BadZipFile, json.JSONDecodeError, KeyError)):
        before = self.store.card(self.card_id).copy()
        with self.assertRaises(errors):
            stage_import(path, self.store.root)
        self.assertEqual(self.store.card(self.card_id), before)
        self.assert_db_ok()
        self.assertEqual(list(self.store.root.glob('.kanyx-import-*')), [])

    def test_export_import_preserves_unicode_and_attachment_bytes(self):
        text = 'دراسة 🌎 日本語 e\u0301\u200d☀️\x00'
        self.store.update_card(self.card_id, text, text + '\n' * 3, 'Hoch', '', 'مهمة,🚀', [(text, True)])
        src = temporary_file(self.root, '📎العربية.txt', (text * 30).encode('utf8'))
        self.store.add_file(self.card_id, src)
        archive = export_workspace(self.store, self.root / 'unicode.kanyx')
        other_root = self.root / 'recipient'
        receiver = Store(other_root)
        self.addCleanup(receiver.close)
        staged = stage_import(archive, other_root)
        rollback = swap_in_workspace(receiver, staged)
        self.assertTrue(rollback.exists())
        row = receiver.one('SELECT * FROM cards WHERE title=?', (text,))
        self.assertIsNotNone(row)
        self.assertEqual(row['description'], text + '\n' * 3)
        self.assertEqual(receiver.card_checks(row['id'])[0]['body'], text)
        attached = receiver.card_files(row['id'])[0]
        self.assertEqual((receiver.attachments / attached['stored_name']).read_bytes(), src.read_bytes())
        self.assertEqual(receiver.verify_integrity(), [])

    def test_corrupt_byte_in_zip_rejected_without_touching_current_data(self):
        valid = self.valid_archive()
        tampered = self.root / 'tampered.kanyx'
        with zipfile.ZipFile(valid) as original, zipfile.ZipFile(tampered, 'w') as output:
            for name in original.namelist():
                data = original.read(name)
                if name == 'workspace.db':
                    data = b'WRONG CONTENT INSTEAD OF THE DATABASE'
                output.writestr(name, data)
        self.assert_rejected_safely(tampered)

    def test_bad_zip_and_invalid_manifest_and_missing_manifest(self):
        bad = self.root / 'truncated.kanyx'
        bad.write_bytes(b'not a zip file')
        self.assert_rejected_safely(bad)
        no_manifest = self.root / 'no-manifest.kanyx'
        with zipfile.ZipFile(no_manifest, 'w') as z:
            z.writestr('workspace.db', b'x')
        self.assert_rejected_safely(no_manifest)
        bad_json = self.root / 'bad-json.kanyx'
        with zipfile.ZipFile(bad_json, 'w') as z:
            z.writestr('manifest.json', '{ not json }')
        self.assert_rejected_safely(bad_json)

    def test_zip_slip_backslash_absolute_path_and_duplicate_entries(self):
        tests = ['../outside.db', 'attachments/../../outside', '/tmp/outside', 'C:\\evil.txt', 'attachments\\bad.txt']
        for i, malicious in enumerate(tests):
            with self.subTest(path=malicious):
                path = self.root / ('bad-path-' + str(i) + '.kanyx')
                with zipfile.ZipFile(path, 'w') as z:
                    z.writestr(malicious, 'oops')
                    z.writestr('manifest.json', '{}')
                self.assert_rejected_safely(path)
        path = self.root / 'duplicate.kanyx'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('manifest.json', '{}')
                z.writestr('manifest.json', '{}')
        self.assert_rejected_safely(path)

    def test_zip_symlink_rejected(self):
        bad = self.root / 'symlink.kanyx'
        info = zipfile.ZipInfo('attachments/shortcut')
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(bad, 'w') as z:
            z.writestr(info, '../../home')
            z.writestr('manifest.json', '{}')
        self.assert_rejected_safely(bad)

    def test_zip_bomb_limits_do_not_need_an_actual_huge_archive(self):
        valid = self.valid_archive()
        with patch.object(portability, 'MAX_UNCOMPRESSED', 3):
            self.assert_rejected_safely(valid)
        with patch.object(portability, 'MAX_FILES', 1):
            self.assert_rejected_safely(valid)

    def test_original_workspace_survives_validation_failures(self):
        archive = self.valid_archive()
        with zipfile.ZipFile(archive) as z:
            manifest = json.loads(z.read('manifest.json'))
            workspace = z.read('workspace.db')
        manifest['files']['workspace.db']['sha256'] = '0' * 64
        bad = self.root / 'wrong-hash.kanyx'
        with zipfile.ZipFile(bad, 'w') as z:
            z.writestr('manifest.json', json.dumps(manifest))
            z.writestr('workspace.db', workspace)
        self.assert_rejected_safely(bad)

    def test_refuses_export_when_source_directory_contains_symlink(self):
        target = temporary_file(self.root, 'private-target.txt', b'secret bytes')
        symlink = self.store.attachments / 'linked.txt'
        try:
            symlink.symlink_to(target)
        except (NotImplementedError, PermissionError, OSError):
            self.skipTest('This OS/account cannot create symlinks')
        with self.assertRaises(ValueError):
            export_workspace(self.store, self.root / 'bad-symlink.kanyx')


os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QDialog
    import ui
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'PySide6 not installed; GUI tests run on Windows with the app environment')
class ChaosGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kanyx-chaos-ui-')
        self.store = Store(Path(self.temp.name) / 'workspace')
        self.window = ui.MainWindow(self.store)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()  # closes SQLite too
        self.app.processEvents()
        self.temp.cleanup()

    def lane_id(self):
        return self.store.rows('SELECT id FROM lanes ORDER BY id LIMIT 1')[0]['id']

    def test_unicode_editor_save_reload_and_search(self):
        for phrase in ('العربية 日本語 हिन्दी 🇦🇹', '中文\u200b✅', '<b>literal HTML</b>', '🦊🔥\u0301'):
            with self.subTest(title=phrase):
                cid = self.store.add_card(self.lane_id(), 'placeholder')
                dialog = ui.CardDialog(self.window, cid)
                dialog.title.setText(phrase)
                dialog.desc.setPlainText(phrase + '\n**Markdown**')
                dialog.tags.setText('🧪,日本語')
                dialog.add_check('✅ ' + phrase)
                dialog.save()
                self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
                self.assertEqual(self.store.card(cid)['title'], phrase)
                self.assertEqual(self.store.card(cid)['description'], phrase + '\n**Markdown**')
                self.assertEqual(self.store.card_checks(cid)[0]['body'], '✅ ' + phrase)
                reopened = ui.CardDialog(self.window, cid)
                self.assertEqual(reopened.title.text(), phrase)
                self.assertEqual(reopened.desc.toPlainText(), phrase + '\n**Markdown**')
                reopened.reject()

    def test_empty_attachment_with_extension_only_and_no_extension(self):
        cid = self.store.add_card(self.lane_id(), 'file matrix')
        sources = []
        for name in ('justfile', '.txt', 'empty😀.bin', 'ملف🦊.dat'):
            path = Path(self.temp.name) / name
            path.write_bytes(b'' if 'empty' in name else b'\x00abc')
            sources.append(path)
        dialog = ui.CardDialog(self.window, cid)
        with patch.object(ui.QFileDialog, 'getOpenFileNames', return_value=([str(x) for x in sources], '')):
            dialog.attach()
        self.assertEqual(dialog.files.count(), len(sources))
        dialog.save()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(len(self.store.card_files(cid)), len(sources))
        self.assertEqual(self.store.verify_integrity(), [])

    def test_file_disappears_between_picker_and_save_no_ghost_attachment(self):
        cid = self.store.add_card(self.lane_id(), 'original title')
        selected = Path(self.temp.name) / 'disappears.txt'
        selected.write_bytes(b'gonna vanish')
        dialog = ui.CardDialog(self.window, cid)
        with patch.object(ui.QFileDialog, 'getOpenFileNames', return_value=([str(selected)], '')):
            dialog.attach()
        selected.unlink()
        with patch.object(ui.QMessageBox, 'warning') as warning:
            dialog.save()
        warning.assert_called()
        self.assertEqual(self.store.card_files(cid), [])
        self.assertEqual(dialog.result(), QDialog.DialogCode.Rejected)

    def test_missing_attachment_open_must_warn_instead_of_opening_regression(self):
        """Missing saved files must show a warning rather than launch."""
        cid = self.store.add_card(self.lane_id(), 'missing attachment')
        source = Path(self.temp.name) / 'missing.docx'
        source.write_bytes(b'doc')
        fid = self.store.add_file(cid, source)
        row = self.store.one('SELECT * FROM files WHERE id=?', (fid,))
        (self.store.attachments / row['stored_name']).unlink()
        dialog = ui.CardDialog(self.window, cid)
        item = dialog.files.item(0)
        with patch.object(ui.QDesktopServices, 'openUrl') as open_url, \
             patch.object(ui.QMessageBox, 'warning') as warning:
            dialog.open_file(item)
        open_url.assert_not_called()
        warning.assert_called_once()

    def test_new_card_with_missing_attachment_leaves_no_partial_card(self):
        selected = Path(self.temp.name) / 'file-gone.bin'
        selected.write_bytes(b'gone soon')
        dialog = ui.CardDialog(self.window, None, is_new=True,
                               lane_id=self.lane_id(), initial_title='should rollback')
        with patch.object(ui.QFileDialog, 'getOpenFileNames', return_value=([str(selected)], '')):
            dialog.attach()
        selected.unlink()
        with patch.object(ui.QMessageBox, 'warning'):
            dialog.save()
        self.assertIsNone(self.store.one('SELECT id FROM cards WHERE title=?', ('should rollback',)))
        self.assertEqual(self.store.verify_integrity(), [])

    def test_edit_failure_is_atomic_regression(self):
        """Regression: failure during attachment save must restore previous card fields."""
        cid = self.store.add_card(self.lane_id(), 'original title')
        selected = Path(self.temp.name) / 'disappears-before-save'
        selected.write_bytes(b'gone soon')
        dialog = ui.CardDialog(self.window, cid)
        dialog.title.setText('edited title')
        with patch.object(ui.QFileDialog, 'getOpenFileNames', return_value=([str(selected)], '')):
            dialog.attach()
        selected.unlink()
        with patch.object(ui.QMessageBox, 'warning'):
            dialog.save()
        self.assertEqual(self.store.card(cid)['title'], 'original title')


if __name__ == '__main__':
    unittest.main()
