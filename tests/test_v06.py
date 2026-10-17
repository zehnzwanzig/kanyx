import tempfile
import unittest
from pathlib import Path
from db import Store

class Version06Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)
        self.bid = self.store.rows('SELECT id FROM boards')[0]['id']
        self.lid = self.store.rows('SELECT id FROM lanes WHERE board_id=?', (self.bid,))[0]['id']
    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_archive_and_restore(self):
        cid = self.store.add_card(self.lid, 'Important card')
        self.store.archive_card(cid)
        self.assertFalse(any(c['id'] == cid for c in self.store.search_cards(self.bid)))
        self.assertEqual([cid], [c['id'] for c in self.store.archived_cards(self.bid)])
        self.store.archive_card(cid,False)
        self.assertEqual([],self.store.archived_cards(self.bid))
        self.assertTrue(any(c['id'] == cid for c in self.store.search_cards(self.bid)))

    def test_duplicate_card_and_attachments_are_independent(self):
        cid = self.store.add_card(self.lid,'Source')
        self.store.update_card(cid,'Source','Description','High','2026-10-17','tag1', [('Step', True)])
        f = Path(self.tmp.name)/'attachment.txt'
        f.write_text('Hello')
        self.store.add_file(cid,f)
        new = self.store.duplicate_card(cid)
        self.assertEqual('Description',self.store.card(new)['description'])
        self.assertEqual(['tag1'],self.store.card_tags(new))
        self.assertEqual(self.store.card_checks(cid), self.store.card_checks(new))
        self.assertNotEqual(self.store.card_files(cid)[0]['stored_name'],self.store.card_files(new)[0]['stored_name'])
        self.store.delete_card(cid)
        self.assertTrue((self.store.attachments/self.store.card_files(new)[0]['stored_name']).exists())

    def test_duplicate_board_and_collapse(self):
        self.store.add_card(self.lid, 'A')
        self.store.set_lane_collapsed(self.lid, True)
        other = self.store.duplicate_board(self.bid)
        lanes = self.store.rows('SELECT * FROM lanes WHERE board_id=? ORDER BY position', (other,))
        self.assertEqual(3,len(lanes))
        self.assertEqual(1,lanes[0]['collapsed'])
        self.assertEqual(1,len(self.store.search_cards(other)))
        self.store.close()
        self.store = Store(self.tmp.name)
        self.assertEqual(1,self.store.one('SELECT collapsed FROM lanes WHERE id=?',(self.lid,))['collapsed'])

if __name__ == '__main__': unittest.main()
