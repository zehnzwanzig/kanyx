"""Regression checks for Kanyx Swimlane RC visual behavior.

Run with: py -m unittest discover -s tests -p test_rc_visual_fix.py -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from PySide6.QtWidgets import QApplication, QFrame, QPushButton
    from db import Store
    import ui
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'PySide6 is required for GUI tests')
class SwimlaneVisualRegressionTests(unittest.TestCase):
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

    def test_undo_redo_buttons_have_normal_unconstrained_width(self):
        buttons = self.window.toolbar_content.findChildren(QPushButton)
        undo = [button for button in buttons if button.text() == '↶']
        redo = [button for button in buttons if button.text() == '↷']
        self.assertEqual(len(undo), 1)
        self.assertEqual(len(redo), 1)
        # A setFixedSize(44, 42) button has maximumWidth() == 44.
        self.assertGreater(undo[0].maximumWidth(), 80)
        self.assertGreater(redo[0].maximumWidth(), 80)

    def test_swimlane_frame_does_not_restyle_nested_columns_or_cards(self):
        bid = self.window.board_id()
        self.store.set_setting(f'swimlane_enabled_{bid}', '1')
        self.window.refresh()
        self.app.processEvents()

        frames = self.window.findChildren(QFrame, 'swimlaneRow')
        self.assertTrue(frames, 'Visible swimlane frames should have an object name')
        for frame in frames:
            css = frame.styleSheet()
            self.assertIn('QFrame#swimlaneRow', css)
            self.assertIn('background: transparent;', css)
            self.assertNotIn('QFrame {', css)

        columns = self.window.findChildren(ui.DropColumn)
        self.assertTrue(columns, 'Swimlane mode must still display columns')
        # Columns use the original app theme, not an inherited local QFrame rule.
        self.assertTrue(all(column.styleSheet() == '' for column in columns))

    def test_classic_board_still_has_original_columns(self):
        bid = self.window.board_id()
        self.store.set_setting(f'swimlane_enabled_{bid}', '0')
        self.window.refresh()
        self.app.processEvents()
        self.assertFalse(self.window.findChildren(QFrame, 'swimlaneRow'))
        self.assertTrue(self.window.findChildren(ui.DropColumn))


if __name__ == '__main__':
    unittest.main()
