"""Regression tests for Windows user feedback after Kanyx 1.0.0-rc.1.

Run headlessly using the Qt offscreen platform plugin. Tests are skipped when
PySide6 is unavailable (the CI environment installs it from requirements.txt).
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

try:
    from PySide6.QtCore import Qt, QPoint, QPointF
    from PySide6.QtWidgets import QApplication, QDialog
    from db import Store
    import ui
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'PySide6 is required for GUI tests')
class WindowsFeedbackRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
        self.window = ui.MainWindow(self.store)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        self.temp.cleanup()

    def lane_id(self):
        return self.store.one('SELECT id FROM lanes ORDER BY id LIMIT 1')['id']

    def make_card_with_file(self):
        cid = self.store.add_card(self.lane_id(), 'Original')
        source = Path(self.temp.name) / 'attachment.txt'
        source.write_text('this must survive cancel', encoding='utf-8')
        fid = self.store.add_file(cid, source)
        record = self.store.one('SELECT * FROM files WHERE id=?', (fid,))
        return cid, fid, self.store.attachments / record['stored_name']

    def test_new_card_cancel_creates_no_record(self):
        lane = next(c for c in self.window.findChildren(ui.DropColumn) if not c.lane.get('collapsed'))
        before = len(self.store.rows('SELECT * FROM cards'))
        with patch.object(ui, 'ask', return_value='Cancelled task'), \
             patch.object(ui.CardDialog, 'exec', return_value=QDialog.DialogCode.Rejected):
            lane.add_card()
        self.assertEqual(len(self.store.rows('SELECT * FROM cards')), before)

    def test_new_card_save_commits_a_record(self):
        dialog = ui.CardDialog(self.window, None, is_new=True,
                               lane_id=self.lane_id(), initial_title='Saved task')
        dialog.save()
        cards = self.store.rows('SELECT * FROM cards')
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]['title'], 'Saved task')

    def test_attachment_removal_cancel_preserves_file(self):
        cid, fid, stored_path = self.make_card_with_file()
        dialog = ui.CardDialog(self.window, cid)
        dialog.files.setCurrentRow(0)
        dialog.remove_file()
        self.assertEqual(dialog.files.count(), 0)
        self.assertTrue(stored_path.is_file())
        self.assertIsNotNone(self.store.one('SELECT id FROM files WHERE id=?', (fid,)))
        dialog.reject()
        self.assertTrue(stored_path.is_file())
        self.assertIsNotNone(self.store.one('SELECT id FROM files WHERE id=?', (fid,)))

    def test_attachment_removal_save_deletes_file(self):
        cid, fid, stored_path = self.make_card_with_file()
        dialog = ui.CardDialog(self.window, cid)
        dialog.files.setCurrentRow(0)
        dialog.remove_file()
        dialog.save()
        self.assertIsNone(self.store.one('SELECT id FROM files WHERE id=?', (fid,)))
        self.assertFalse(stored_path.exists())

    def test_new_attachment_cancel_does_not_copy_file(self):
        cid = self.store.add_card(self.lane_id(), 'Existing task')
        src = Path(self.temp.name) / 'new-attachment.txt'
        src.write_text('test', encoding='utf-8')
        dialog = ui.CardDialog(self.window, cid)
        with patch.object(ui.QFileDialog, 'getOpenFileNames', return_value=([str(src)], '')):
            dialog.attach()
        self.assertEqual(dialog.files.count(), 1)
        self.assertEqual(self.store.card_files(cid), [])
        dialog.reject()
        self.assertEqual(self.store.card_files(cid), [])
        self.assertFalse(any(self.store.attachments.iterdir()))

    def test_new_attachment_save_copies_file(self):
        cid = self.store.add_card(self.lane_id(), 'Existing task')
        src = Path(self.temp.name) / 'new-attachment.txt'
        src.write_text('test', encoding='utf-8')
        dialog = ui.CardDialog(self.window, cid)
        with patch.object(ui.QFileDialog, 'getOpenFileNames', return_value=([str(src)], '')):
            dialog.attach()
        dialog.save()
        files = self.store.card_files(cid)
        self.assertEqual(len(files), 1)
        self.assertTrue((self.store.attachments / files[0]['stored_name']).is_file())

    def test_import_reapplies_the_saved_appearance(self):
        self.assertEqual(self.store.setting('ui_scale', '100'), '100')
        def fake_swap(store, stage):
            store.set_setting('ui_scale', '135')
            return Path(self.temp.name) / 'previous'
        with patch.object(ui.QFileDialog, 'getOpenFileName', return_value=('example.kanyx', '')), \
             patch.object(ui.QMessageBox, 'warning', return_value=ui.QMessageBox.StandardButton.Yes), \
             patch.object(ui.QMessageBox, 'information'), \
             patch.object(ui, 'stage_import', return_value=Path(self.temp.name)/'staging'), \
             patch.object(ui, 'swap_in_workspace', side_effect=fake_swap):
            self.window.import_workspace()
        self.assertIn('font-size: 18px', self.app.styleSheet())  # round(13 * 1.35)

    def test_toolbar_scrolls_instead_of_overlap_at_140_percent(self):
        self.store.set_setting('ui_scale', '140')
        self.window.resize(780, 550)
        self.window.apply_visual_settings()
        self.app.processEvents()
        self.assertGreater(self.window.tools_scroll.horizontalScrollBar().maximum(), 0)
        search_right = self.window.search.mapTo(self.window, QPoint(self.window.search.width(), 0)).x()
        filter_left = self.window.priority.mapTo(self.window, QPoint(0, 0)).x()
        self.assertLessEqual(search_right, filter_left + 2)
        self.assertGreaterEqual(self.window.search.width(), 120)

    def test_dragged_column_has_translucent_preview(self):
        handle = self.window.findChildren(ui.LaneDragHandle)[0]
        handle.start = QPoint(5, 5)
        class FakeMouseMove:
            def buttons(self): return Qt.MouseButton.LeftButton
            def position(self): return QPointF(35, 35)
        with patch.object(ui, 'QDrag') as drag_factory:
            handle.mouseMoveEvent(FakeMouseMove())
            drag_factory.return_value.setPixmap.assert_called_once()
            image = drag_factory.return_value.setPixmap.call_args.args[0]
            self.assertTrue(image.hasAlphaChannel())


if __name__ == '__main__':
    unittest.main()
