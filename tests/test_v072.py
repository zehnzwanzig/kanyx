import unittest
from pathlib import Path

class MarkdownInitialModeTests(unittest.TestCase):
    def test_new_and_existing_card_modes_are_distinct(self):
        ui = (Path(__file__).resolve().parents[1] / 'ui.py').read_text(encoding='utf-8')
        self.assertIn('self.window.edit_card(cid, is_new=True)', ui)
        self.assertIn('def edit_card(self, cid, is_new=False):', ui)
        self.assertIn('CardDialog(self,cid,is_new=is_new).exec()', ui)
        self.assertIn('def __init__(self, window, cid, is_new=False):', ui)
        self.assertIn('self.markdown_toggle.setChecked(not is_new)', ui)
        self.assertIn('self.preview.setMarkdown(self.desc.toPlainText())', ui)
        self.assertIn('self.desc.setPlainText(card[\'description\'] or \'\')', ui)

if __name__ == '__main__':
    unittest.main()
