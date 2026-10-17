import tempfile
import unittest
from pathlib import Path
from db import Store

class StoreTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            s = Store(temp)
            bid = s.rows('SELECT id FROM boards')[0]['id']
            lanes = s.rows('SELECT * FROM lanes WHERE board_id=? ORDER BY position',(bid,))
            cid = s.add_card(lanes[0]['id'],'Test')
            s.update_card(cid,'Geändert','Text','Hoch','2026-12-01','alpha, beta', [('Punkt',True)])
            self.assertEqual(s.card(cid)['priority'],'Hoch')
            self.assertEqual(s.card_tags(cid),['alpha','beta'])
            self.assertEqual(s.card_checks(cid)[0]['done'],1)
            s.move_card(cid,lanes[1]['id'],0)
            self.assertEqual(s.card(cid)['lane_id'],lanes[1]['id'])
            self.assertEqual(len(s.search_cards(bid,'alpha')),1)
            attachment = Path(temp)/'hello.txt'
            attachment.write_text('hello')
            s.add_file(cid,attachment)
            self.assertEqual(len(s.card_files(cid)),1)
            s.delete_card(cid)
            self.assertEqual(len(list(s.attachments.iterdir())),0)
            s.close()

if __name__ == '__main__': unittest.main()
