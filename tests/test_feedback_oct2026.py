"""October 2026 usability regression tests (filters and collapsed columns)."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

try:
    from PySide6.QtWidgets import QApplication, QPushButton
    from db import Store
    from i18n import LANGUAGES, tr
    import ui
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'PySide6 is required for GUI tests')
class FeedbackOctober2026Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
        self.board = self.store.rows('SELECT id FROM boards ORDER BY id LIMIT 1')[0]['id']
        self.lane = self.store.rows('SELECT id FROM lanes WHERE board_id=? ORDER BY position', (self.board,))[0]['id']
        self.store.add_card(self.lane, 'Visible task')
        self.window = ui.MainWindow(self.store)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        self.temp.cleanup()

    def test_search_filter_is_obvious_and_reset_is_available(self):
        self.assertFalse(self.window.filter_notice.isVisible())
        self.window.search.setText('no-such-task')
        self.app.processEvents()
        self.assertTrue(self.window.filter_notice.isVisible())
        self.assertIn('0 / 1', self.window.filter_notice_label.text())
        self.assertIn('border: 2px', self.window.search.styleSheet())
        reset = self.window.filter_notice.findChild(QPushButton, 'clearFiltersButton')
        self.assertIsNotNone(reset)
        reset.click()
        self.app.processEvents()
        self.assertEqual(self.window.search.text(), '')
        self.assertFalse(self.window.filter_notice.isVisible())

    def test_priority_filter_shows_banner_and_reset(self):
        self.window.priority.setCurrentIndex(2)  # Low/Normal order depends on index, any != All.
        self.app.processEvents()
        self.assertTrue(self.window.filter_notice.isVisible())
        self.assertNotEqual(self.window.priority.styleSheet(), '')
        self.window.clear_filters()
        self.app.processEvents()
        self.assertFalse(self.window.filter_notice.isVisible())
        self.assertEqual(self.window.priority.currentData(), 'Alle')

    def test_collapsed_column_has_one_clear_button_and_no_loose_triangle(self):
        self.store.set_lane_collapsed(self.lane, True)
        self.window.refresh()
        self.app.processEvents()
        column = next(x for x in self.window.findChildren(ui.DropColumn)
                      if x.lane['id'] == self.lane)
        toggle = column.findChild(QPushButton, 'columnToggle')
        self.assertIsNotNone(toggle)
        self.assertEqual(toggle.text(), '›')
        self.assertEqual(toggle.toolTip(), tr('en', 'Expand column'))
        self.assertEqual(toggle.width(), 34)
        toggle.click()
        self.app.processEvents()
        self.assertEqual(self.store.one('SELECT collapsed FROM lanes WHERE id=?', (self.lane,))['collapsed'], 0)

    def test_all_six_new_languages_are_switchable_and_persist(self):
        for code in ('it', 'zh_CN', 'pt_BR', 'pl', 'ru', 'hi'):
            self.assertIn(code, LANGUAGES)
            self.assertNotEqual(tr(code, 'Save'), 'Save')
            self.assertNotEqual(tr(code, 'Clear filters'), 'Clear filters')
            self.window.language_select.setCurrentIndex(self.window.language_select.findData(code))
            self.app.processEvents()
            self.assertEqual(self.store.setting('language'), code)
            self.assertEqual(self.window.language, code)


if __name__ == '__main__':
    unittest.main()
