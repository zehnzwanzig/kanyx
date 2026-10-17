import tempfile
import unittest
from pathlib import Path
from db import Store

class MarkdownSourceRegressionTests(unittest.TestCase):
    def test_html_markdown_source_survives_database_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory)
            board = store.rows('SELECT id FROM boards LIMIT 1')[0]['id']
            lane = store.rows('SELECT id FROM lanes WHERE board_id=?', (board,))[0]['id']
            card = store.add_card(lane, 'Markdown regression')
            source = '<b>Test</b>\n\n**more bold**\n- item'
            store.update_card(card, 'Markdown regression', source, 'Normal', '', '', [])
            self.assertEqual(store.card(card)['description'], source)
            store.close()
            store = Store(directory)
            self.assertEqual(store.card(card)['description'], source)
            store.close()

    def test_editor_uses_explicit_plain_text_loading(self):
        ui = (Path(__file__).resolve().parents[1] / 'ui.py').read_text(encoding='utf-8')
        self.assertIn("self.desc.setPlainText(card['description'] or '')", ui)
        self.assertIn('self.desc.setAcceptRichText(False)', ui)
        self.assertIn('self.markdown_toggle.setCheckable(True)', ui)
        self.assertIn('self.card_color.addItem(QIcon(swatch)', ui)

if __name__ == '__main__': unittest.main()
