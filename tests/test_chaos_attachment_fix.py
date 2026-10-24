"""Regression coverage for the five chaos bugs and keep-vs-delete choice.

All files live in TemporaryDirectory. Qt checks skip without PySide6.
"""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from db import Store
from portability import export_workspace


class AttachmentLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kanyx-fix-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'workspace')
        self.addCleanup(self.store.close)
        self.lane = self.store.rows('SELECT id FROM lanes ORDER BY id LIMIT 1')[0]['id']
        self.cid = self.store.add_card(self.lane, 'Original')

    def attachment(self, name='test.bin', contents=b'important'):
        src = self.root / name
        src.write_bytes(contents)
        fid = self.store.add_file(self.cid, src)
        row = self.store.one('SELECT * FROM files WHERE id=?', (fid,))
        return fid, self.store.attachments / row['stored_name']

    def test_keep_attachment_deletes_card_and_reference_only(self):
        fid, stored = self.attachment('keep.pdf', b'please keep')
        self.store.delete_card(self.cid, delete_attachments=False)
        self.assertIsNone(self.store.card(self.cid))
        self.assertIsNone(self.store.one('SELECT id FROM files WHERE id=?', (fid,)))
        self.assertEqual(stored.read_bytes(), b'please keep')
        archive = export_workspace(self.store, self.root / 'retained.kanyx')
        import zipfile
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(z.read('attachments/' + stored.name), b'please keep')

    def test_delete_attachment_and_card_removes_file(self):
        _, stored = self.attachment()
        self.store.delete_card(self.cid, delete_attachments=True)
        self.assertIsNone(self.store.card(self.cid))
        self.assertFalse(stored.exists())

    def test_default_still_deletes_files(self):
        _, stored = self.attachment()
        self.store.delete_card(self.cid)
        self.assertFalse(stored.exists())

    def test_corrupt_db_path_cannot_delete_file_outside_attachments(self):
        fid, _ = self.attachment()
        protected = self.store.data / 'protected.txt'
        protected.write_bytes(b'untouched')
        self.store.execute('UPDATE files SET stored_name=? WHERE id=?', ('../protected.txt', fid))
        self.store.delete_card(self.cid)
        self.assertEqual(protected.read_bytes(), b'untouched')
        self.assertIsNone(self.store.card(self.cid))

    def test_corrupt_db_path_windows_style_is_not_followed(self):
        fid, _ = self.attachment()
        protected = self.store.data / 'protected.txt'
        protected.write_bytes(b'untouched')
        self.store.execute('UPDATE files SET stored_name=? WHERE id=?', (r'..\protected.txt', fid))
        self.store.delete_file(fid)
        self.assertEqual(protected.read_bytes(), b'untouched')

    def test_multi_file_delete_restores_when_move_fails(self):
        self.attachment('a.txt')
        self.attachment('b.txt')
        rows = self.store.card_files(self.cid)
        filenames = [self.store.attachments / row['stored_name'] for row in rows]
        real_replace = os.replace
        called = [0]
        def failing_replace(src, dst):
            called[0] += 1
            if called[0] == 2:
                raise PermissionError('second attachment locked')
            return real_replace(src, dst)
        with patch('db.os.replace', side_effect=failing_replace):
            with self.assertRaises(PermissionError):
                self.store.delete_card(self.cid)
        self.assertIsNotNone(self.store.card(self.cid))
        self.assertEqual(len(self.store.card_files(self.cid)),2)
        self.assertTrue(all(p.exists() for p in filenames))
        self.assertFalse(any(p.name.startswith('.kanyx-trash') for p in self.store.attachments.iterdir()))

    def test_failure_after_copy_rolls_back_changed_fields_and_new_file(self):
        candidate = self.root / 'next.pdf'
        candidate.write_bytes(b'text')
        with self.assertRaises(ValueError):
            self.store.save_card_with_files(self.cid, 'Edited', 'Updated', 'Normal', '', '', [],
                                            color='not-a-valid-color', added_paths=[candidate])
        self.assertEqual(self.store.card(self.cid)['title'], 'Original')
        self.assertEqual(self.store.card_files(self.cid), [])
        self.assertEqual(list(self.store.attachments.iterdir()), [])

    def test_missing_new_attachment_does_not_modify_old_card(self):
        missing = self.root / 'absent_file.zip'
        with self.assertRaises(OSError):
            self.store.save_card_with_files(self.cid, 'Edited', '', 'Normal', '', '', [], added_paths=[missing])
        self.assertEqual(self.store.card(self.cid)['title'], 'Original')

    def test_new_card_failed_save_leaves_no_card(self):
        missing = self.root / 'absent_file.zip'
        with self.assertRaises(OSError):
            self.store.save_card_with_files(None, 'Unwanted', '', 'Normal', '', '', [],
                                            is_new=True, lane_id=self.lane, added_paths=[missing])
        self.assertIsNone(self.store.one('SELECT id FROM cards WHERE title=?', ('Unwanted',)))

    def test_successful_multi_file_edit_with_removed_attachment(self):
        old_id, old_file = self.attachment()
        fresh = self.root / 'fresh.txt'
        fresh.write_bytes(b'fresh')
        self.store.save_card_with_files(self.cid, 'Edited', 'new description', 'Normal', '', 'tag, TAG',
                                        [('do thing', True)], added_paths=[fresh], removed_ids=[old_id])
        self.assertFalse(old_file.exists())
        self.assertEqual(self.store.card(self.cid)['title'], 'Edited')
        self.assertEqual(len(self.store.card_files(self.cid)),1)
        self.assertEqual(len(self.store.card_tags(self.cid)),1)
        self.assertEqual(self.store.verify_integrity(), [])
        self.store.verify_integrity_sqlite()

    def test_like_metacharacters_are_literal(self):
        self.store.update_card(self.cid, 'default title', '', 'Normal', '', '', [])
        for term in ('%', '_', '!'):
            self.assertEqual(self.store.search_cards(self.store.one('SELECT board_id FROM lanes WHERE id=?',(self.lane,))['board_id'],term),[])
        self.store.update_card(self.cid, 'has !_ % literal', '', 'Normal', '', '', [])
        self.assertEqual(len(self.store.search_cards(self.store.one('SELECT board_id FROM lanes WHERE id=?',(self.lane,))['board_id'],'!_')),1)


os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
    from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
    from PySide6.QtCore import Qt
    from i18n import LANGUAGES, tr
    import ui
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'PySide6 not installed')
class AttachmentChoiceGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kanyx-gui-fix-')
        self.store = Store(Path(self.temp.name) / 'workspace')
        self.window = ui.MainWindow(self.store)
        self.window.show()
        self.app.processEvents()
        lane = self.store.rows('SELECT id FROM lanes ORDER BY id LIMIT 1')[0]['id']
        self.cid = self.store.add_card(lane, 'Keep or delete?')
        src = Path(self.temp.name) / 'memo.txt'
        src.write_text('Keep this', encoding='utf8')
        self.store.add_file(self.cid, src)
        row = self.store.card_files(self.cid)[0]
        self.stored = self.store.attachments / row['stored_name']
        self.dialog = ui.CardDialog(self.window,self.cid)

    def tearDown(self):
        self.dialog.close()
        self.window.close()
        self.app.processEvents()
        self.temp.cleanup()

    def choose(self, choice_key):
        # Avoid exec() showing a modal window; simulate the selected button.
        def picked(box):
            desired=tr(self.window.language, choice_key)
            return next(button for button in box.buttons() if button.text()==desired)
        with patch.object(ui.QMessageBox,'exec',return_value=0), \
             patch.object(ui.QMessageBox,'clickedButton',new=picked):
            self.dialog.delete()

    def test_keep_files_choice_removes_card_only(self):
        self.choose('Keep attachments')
        self.assertIsNone(self.store.card(self.cid))
        self.assertEqual(self.stored.read_bytes(), b'Keep this')
        self.assertEqual(self.dialog.result(),QDialog.DialogCode.Accepted)

    def test_delete_files_choice_removes_both(self):
        self.choose('Delete attachments')
        self.assertIsNone(self.store.card(self.cid))
        self.assertFalse(self.stored.exists())

    def test_cancel_does_not_delete(self):
        self.choose('Cancel')
        self.assertIsNotNone(self.store.card(self.cid))
        self.assertTrue(self.stored.is_file())

    def test_delete_dialog_is_translated_in_all_languages(self):
        keys=('Keep attachments','Delete attachments',
              'This task has attachments. What should happen to them?',
              'Attachment is missing or unsafe.')
        for lang in LANGUAGES:
            for key in keys:
                self.assertTrue(tr(lang,key))
                if lang != 'en':
                    self.assertNotEqual(tr(lang,key),key)


if __name__=='__main__':
    unittest.main()
