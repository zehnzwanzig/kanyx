"""Regression tests for 13th language and live column reorder insertion guide."""
import os
import tempfile
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from i18n import LANGUAGES, TRANSLATIONS, ROWS, tr


class NewLocalizationTests(unittest.TestCase):
    def test_thirteen_languages_and_complete_arabic_catalog(self):
        self.assertEqual(len(LANGUAGES), 13)
        self.assertEqual(LANGUAGES['ar'], 'العربية')
        expected = {row[0] for row in ROWS} | {
            'Filters active', 'Clear filters', 'Expand column', 'Collapse column'
        }
        self.assertEqual(set(TRANSLATIONS['ar']), expected)
        for language in LANGUAGES:
            for key in ('Filters active', 'Clear filters', 'Expand column', 'Collapse column'):
                self.assertTrue(tr(language, key))
                if language != 'en':
                    self.assertNotEqual(tr(language, key), key)


try:
    from PySide6.QtCore import Qt, QMimeData
    from PySide6.QtWidgets import QApplication, QPushButton
    from db import Store
    import ui
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'PySide6 required for GUI tests')
class DragGuideAndArabicGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
        self.board_id = self.store.rows('SELECT id FROM boards ORDER BY id LIMIT 1')[0]['id']
        self.source_id = self.store.rows(
            'SELECT id FROM lanes WHERE board_id=? ORDER BY position,id',
            (self.board_id,))[0]['id']
        self.target_id = self.store.add_lane(self.board_id, 'Target for drag test')
        self.window = ui.MainWindow(self.store)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        self.temp.cleanup()

    def col(self, lane_id):
        return next(x for x in self.window.findChildren(ui.DropColumn)
                    if x.lane['id'] == lane_id)

    def test_insertion_marker_uses_same_threshold_as_drop(self):
        source, target = self.col(self.source_id), self.col(self.target_id)
        mime = QMimeData()
        mime.setData('application/x-kanyx-lane', str(self.source_id).encode('ascii'))
        target.set_lane_drop_side(mime, 2)
        self.assertEqual(target._lane_drop_side, 'before')
        target.set_lane_drop_side(mime, target.width() / 2 - 1)
        self.assertEqual(target._lane_drop_side, 'before')
        target.set_lane_drop_side(mime, target.width() / 2)
        self.assertEqual(target._lane_drop_side, 'after')
        target.set_lane_drop_side(mime, target.width() - 2)
        self.assertEqual(target._lane_drop_side, 'after')
        target.clear_lane_drop_side()
        self.assertIsNone(target._lane_drop_side)
        source.set_lane_drop_side(mime, source.width() - 1)
        self.assertIsNone(source._lane_drop_side)  # moving over itself is a no-op

    def test_arabic_switch_right_to_left_input_and_translated_filter(self):
        german_index = self.window.language_select.findData('de')
        self.window.language_select.setCurrentIndex(german_index)
        self.window.search.setText('not-present')
        self.app.processEvents()
        self.assertIn('Filter aktiv', self.window.filter_notice_label.text())
        btn = self.window.filter_notice.findChild(QPushButton, 'clearFiltersButton')
        self.assertEqual(btn.text(), 'Filter zurücksetzen')
        arabic_index = self.window.language_select.findData('ar')
        self.window.language_select.setCurrentIndex(arabic_index)
        self.app.processEvents()
        self.assertEqual(self.window.search.layoutDirection(), Qt.LayoutDirection.RightToLeft)
        self.assertIn('عوامل التصفية مفعّلة', self.window.filter_notice_label.text())
        btn = self.window.filter_notice.findChild(QPushButton, 'clearFiltersButton')
        self.assertEqual(btn.text(), 'مسح عوامل التصفية')
        self.assertEqual(self.store.setting('language'), 'ar')
        btn.click()
        self.app.processEvents()
        self.assertFalse(self.window.filter_notice.isVisible())


if __name__ == '__main__':
    unittest.main()
