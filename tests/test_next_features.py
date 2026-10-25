"""Backward-compatible acceptance tests for optional Swimlanes and Due-date Calendar.
Run via: py -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import sqlite3
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from db import Store
from kanyx_feature_core import (migrate_swimlanes, swimlanes, add_swimlane,
    delete_swimlane, move_swimlane, default_swimlane, assign_swimlane,
    move_card_to_swimlane, due_cards, set_due)

class SwimlaneDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(self.tmp.name)
        self.bid=self.store.rows('SELECT id FROM boards')[0]['id']
        self.lanes=self.store.rows('SELECT id FROM lanes WHERE board_id=? ORDER BY position,id',(self.bid,))
        self.lid=self.lanes[0]['id']
    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()
    def test_old_sqlite_data_is_migrated_without_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory)/'data'
            data.mkdir()
            con=sqlite3.connect(data/'kanyx.db')
            con.execute('CREATE TABLE boards(id INTEGER PRIMARY KEY,title TEXT,position INTEGER)')
            con.execute('CREATE TABLE lanes(id INTEGER PRIMARY KEY,board_id INTEGER,title TEXT,position INTEGER)')
            con.execute('CREATE TABLE cards(id INTEGER PRIMARY KEY,lane_id INTEGER,title TEXT,position INTEGER)')
            con.execute("INSERT INTO boards VALUES(5,'Legacy',0)")
            con.execute("INSERT INTO lanes VALUES(9,5,'To Do',0)")
            con.execute("INSERT INTO cards VALUES(17,9,'Keep me',0)")
            con.commit();con.close()
            old=Store(directory)
            self.assertEqual(old.card(17)['title'],'Keep me')
            self.assertEqual(old.card(17)['swimlane_id'],default_swimlane(old,5))
            self.assertEqual(old.verify_integrity_sqlite(),None)
            old.close()

    def test_default_swimlane_created_and_is_repeatable(self):
        self.assertEqual(len(swimlanes(self.store,self.bid)),1)
        sid=default_swimlane(self.store,self.bid)
        cid=self.store.add_card(self.lid,'old-style')
        self.assertEqual(self.store.card(cid)['swimlane_id'],sid)
        migrate_swimlanes(self.store)
        self.assertEqual(len(swimlanes(self.store,self.bid)),1)
        self.assertEqual(self.store.card(cid)['swimlane_id'],sid)
    def test_move_and_order_and_undo_swimlanes(self):
        a=add_swimlane(self.store,self.bid,'Urgent')
        b=add_swimlane(self.store,self.bid,'Normal')
        x=self.store.add_card(self.lid,'one')
        y=self.store.add_card(self.lid,'two')
        self.assertEqual(self.store.card(x)['swimlane_id'],default_swimlane(self.store,self.bid))
        move_card_to_swimlane(self.store,x,self.lid,0,a)
        move_card_to_swimlane(self.store,y,self.lid,0,a)
        self.assertEqual(self.store.card(x)['swimlane_id'],a)
        self.assertEqual(self.store.card(y)['swimlane_id'],a)
        self.assertEqual(self.store.rows('SELECT id FROM cards WHERE lane_id=? AND swimlane_id=? ORDER BY position',(self.lid,a)), [{'id':y},{'id':x}])
        move_swimlane(self.store,b,0)
        self.assertEqual(swimlanes(self.store,self.bid)[0]['id'],b)
        delete_swimlane(self.store,a)
        default=default_swimlane(self.store,self.bid)
        self.assertEqual(self.store.card(x)['swimlane_id'],default)
        self.assertEqual(self.store.card(y)['swimlane_id'],default)
    def test_swimlane_is_board_scoped(self):
        a=add_swimlane(self.store,self.bid,'Only board 1')
        bid2=self.store.add_board('Second')
        lid2=self.store.add_lane(bid2,'To Do')
        cid=self.store.add_card(lid2,'Board 2')
        with self.assertRaises(ValueError):
            assign_swimlane(self.store,cid,a)
        with self.assertRaises(ValueError):
            move_card_to_swimlane(self.store,cid,self.lid,0,a)
    def test_duplicate_board_and_card_preserve_corresponding_group(self):
        a=add_swimlane(self.store,self.bid,'Bugs')
        cid=self.store.add_card(self.lid,'test')
        assign_swimlane(self.store,cid,a)
        clone=self.store.duplicate_card(cid)
        self.assertEqual(self.store.card(clone)['swimlane_id'],a)
        copied_board=self.store.duplicate_board(self.bid)
        swim=swimlanes(self.store,copied_board)
        self.assertEqual(len(swim),2)
        self.assertEqual({s['title'] for s in swim},{'General','Bugs'})
        copied=self.store.rows('''SELECT c.swimlane_id FROM cards c JOIN lanes l ON l.id=c.lane_id WHERE l.board_id=?''',(copied_board,))
        matched={s['id'] for s in swim if s['title']=='Bugs'}
        self.assertTrue(copied)
        self.assertTrue(all(c['swimlane_id'] in matched for c in copied))
    def test_due_date_calendar_queries_and_date_change(self):
        a=self.store.add_card(self.lid,'Due')
        b=self.store.add_card(self.lid,'None')
        set_due(self.store,a,'2030-12-25')
        self.assertEqual([c['id'] for c in due_cards(self.store,self.bid)],[a])
        set_due(self.store,a,'2030-12-26')
        self.assertEqual(self.store.card(a)['due'],'2030-12-26')
        set_due(self.store,a,'')
        self.assertEqual(due_cards(self.store,self.bid),[])
        with self.assertRaises(ValueError):
            set_due(self.store,b,'2030-99-99')
    def test_swimlane_survives_kanyx_roundtrip(self):
        from portability import export_workspace,stage_import,swap_in_workspace
        a=add_swimlane(self.store,self.bid,'External')
        cid=self.store.add_card(self.lid,'test')
        assign_swimlane(self.store,cid,a)
        zip_path=Path(self.tmp.name)/'workspace.kanyx'
        export_workspace(self.store,zip_path)
        stage=stage_import(zip_path,Path(self.tmp.name))
        rollback=swap_in_workspace(self.store,stage)
        migrate_swimlanes(self.store)
        self.assertTrue(rollback.exists())
        self.assertEqual(self.store.card(cid)['swimlane_id'],a)
        self.assertEqual(len(swimlanes(self.store,self.bid)),2)

try:
    from PySide6.QtWidgets import QApplication
    from kanyx_feature_ui import DueDateCalendarDialog, t, LANG
    from ui import MainWindow
    HAS_QT=True
except ImportError:
    HAS_QT=False

@unittest.skipUnless(HAS_QT,'PySide6 required for GUI feature tests')
class FeatureGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(self.tmp.name)
        self.window=MainWindow(self.store)
        self.window.show()
        self.app.processEvents()
    def tearDown(self):
        self.window.close();self.app.processEvents();self.tmp.cleanup()
    def test_features_are_off_by_default(self):
        self.assertEqual(self.store.setting('update_check_on_start','0'),'0')
        self.assertEqual(self.store.setting(f'swimlane_enabled_{self.window.board_id()}','0'),'0')
    def test_swimlane_toggle_and_card_editor(self):
        self.window.toggle_swimlanes()
        self.assertEqual(self.store.setting(f'swimlane_enabled_{self.window.board_id()}'),'1')
        self.assertTrue(self.window.findChildren(__import__('ui').DropColumn))
    def test_calendar_can_show_and_change_due_cards(self):
        lid=self.store.rows('SELECT id FROM lanes LIMIT 1')[0]['id']
        cid=self.store.add_card(lid,'my event')
        set_due(self.store,cid,date.today().isoformat())
        dialog=DueDateCalendarDialog(self.window)
        self.assertTrue(dialog.title.text())
        dialog.mode.setCurrentIndex(dialog.mode.findData('Week'))
        self.assertTrue(dialog.title.text())
        dialog.close()
    def test_translations_cover_all_13_locales(self):
        from i18n import LANGUAGES
        self.assertEqual(set(LANG),set(LANGUAGES))
        for lang in LANGUAGES:
            self.assertEqual(len(LANG[lang]),len(LANG['en']))
            self.assertTrue(t(lang,'Calendar'))

if __name__=='__main__':unittest.main()
