"""Regression checks for the linked swimlane and column opacity.

The transparency relation must update during the Appearance slider preview,
not just after rebuilding the board. It must never style nested card frames.
"""
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

try:
    import ui
except ImportError:
    ui = None


@unittest.skipUnless(ui is not None, 'PySide6 needed for UI CSS regression')
class SwimlaneOpacityTests(unittest.TestCase):
    def test_swimlane_background_alpha_is_half_column_alpha(self):
        for percent in (45, 60, 88, 100):
            with self.subTest(column_opacity=percent):
                css = ui.themed_style(percent)
                column_alpha = round(255 * percent / 100)
                swimlane_alpha = round(255 * percent / 200)
                self.assertIn(
                    f'QFrame#lane {{background-color: rgba(34, 38, 48, {column_alpha});', css)
                self.assertIn(
                    f'QFrame#swimlaneRow {{background-color: rgba(25, 29, 39, {swimlane_alpha});', css)
                self.assertNotIn('__SWIMLANE_ALPHA__', css)

    def test_only_the_swimlane_row_gets_the_background(self):
        source = (Path(__file__).resolve().parents[1] / 'ui.py').read_text(encoding='utf-8-sig')
        self.assertIn("row_widget.setObjectName('swimlaneRow')", source)
        self.assertNotIn('row_widget.setStyleSheet(', source)
        self.assertNotRegex(source, r"QFrame\s*\{[^}]*background-color:\s*rgba\(25")


if __name__ == '__main__':
    unittest.main()
