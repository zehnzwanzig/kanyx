import tempfile
import unittest
from pathlib import Path
from db import Store


class Version07Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_templates(self):
        expected = {'simple': 3, 'project': 5, 'personal': 4, 'blank': 0}
        for template, count in expected.items():
            board = self.store.create_board_from_template('Sample', template)
            lanes = self.store.rows('SELECT * FROM lanes WHERE board_id=? ORDER BY position', (board,))
            self.assertEqual(len(lanes), count)
            self.assertEqual([x['position'] for x in lanes], list(range(count)))
        with self.assertRaises(ValueError):
            self.store.create_board_from_template('Wrong', 'unknown')

    def test_color_and_duplicates(self):
        lane = self.store.one('SELECT id FROM lanes LIMIT 1')['id']
        card = self.store.add_card(lane, 'Example')
        self.store.update_card(card, 'Example', '# Markdown', 'Normal', '', '', [('One', True), ('Two', False)], '#6bb6a4')
        self.assertEqual(self.store.card(card)['color'], '#6bb6a4')
        duplicate = self.store.duplicate_card(card)
        self.assertEqual(self.store.card(duplicate)['color'], '#6bb6a4')
        self.assertEqual(self.store.card(duplicate)['description'], '# Markdown')
        board = self.store.one('SELECT board_id FROM lanes WHERE id=?', (lane,))['board_id']
        board_copy = self.store.duplicate_board(board)
        copied_card = self.store.one('SELECT c.* FROM cards c JOIN lanes l ON l.id=c.lane_id WHERE l.board_id=? ORDER BY c.id LIMIT 1', (board_copy,))
        self.assertEqual(copied_card['color'], '#6bb6a4')
        self.assertEqual(len(self.store.card_checks(duplicate)), 2)

    def test_legacy_schema_upgrade(self):
        lane = self.store.one('SELECT id FROM lanes LIMIT 1')['id']
        card = self.store.add_card(lane, 'Existing task')
        self.store.close()
        import sqlite3
        dbfile = Path(self.temp.name) / 'data' / 'kanyx.db'
        con = sqlite3.connect(dbfile)
        con.execute('ALTER TABLE cards DROP COLUMN color')
        con.close()
        upgraded = Store(Path(self.temp.name))
        self.store = upgraded
        self.assertEqual(upgraded.card(card)['title'], 'Existing task')
        self.assertEqual(upgraded.card(card)['color'], '')
        self.assertTrue(list((Path(self.temp.name) / 'data' / 'backups').glob('before_v07_*.db')))
