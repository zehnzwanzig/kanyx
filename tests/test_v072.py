"""Regression checks: new and existing cards must keep distinct Markdown modes.

The source-code assertions below cover the intentional Swimlane-aware
constructor introduced after Kanyx 1.0.2.
"""
import unittest
from pathlib import Path


class MarkdownInitialModeTests(unittest.TestCase):
    def test_new_and_existing_card_modes_are_distinct(self):
        ui = (Path(__file__).resolve().parents[1] / 'ui.py').read_text(encoding='utf-8')
        self.assertIn(
            "CardDialog(self.window, None, is_new=True, lane_id=self.lane['id'], "
            "initial_title=title, swimlane_id=self.swimlane_id).exec()", ui)
        self.assertIn('def edit_card(self, cid, is_new=False):', ui)
        self.assertIn('CardDialog(self, cid, is_new=is_new).exec()', ui)
        self.assertIn(
            "def __init__(self, window, cid, is_new=False, lane_id=None, "
            "initial_title='', swimlane_id=None):", ui)
        self.assertIn('self.markdown_toggle.setChecked(not is_new)', ui)
        self.assertIn('self.preview.setMarkdown(self.desc.toPlainText())', ui)
        self.assertIn("self.desc.setPlainText(card['description'] or '')", ui)


if __name__ == '__main__':
    unittest.main()
