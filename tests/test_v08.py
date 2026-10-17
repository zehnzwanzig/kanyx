import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from db import Store
from portability import export_workspace, stage_import, swap_in_workspace


class PortableWorkspaceTests(unittest.TestCase):
    def test_complete_round_trip_with_wallpaper_and_attachments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = Store(root / 'first')
            board = original.rows('SELECT id FROM boards')[0]['id']
            lane = original.rows('SELECT id FROM lanes WHERE board_id=?', (board,))[0]['id']
            card = original.add_card(lane, 'Important task')
            original.update_card(card, 'Important task', '<b>formatted</b>', 'Hoch', '', 'alpha', [('done', True)], '#4f98c8')
            attachment = root / 'source.txt'
            attachment.write_text('must survive', encoding='utf8')
            original.add_file(card, attachment)
            wallpaper = root / 'wallpaper.png'
            wallpaper.write_bytes(b'example image content')
            original.set_wallpaper(wallpaper)
            original.set_setting('language','ja')
            exported = export_workspace(original, root / 'workspace.kanyx')
            original.close()

            receiving = Store(root / 'second')
            existing_card = receiving.add_card(receiving.rows('SELECT id FROM lanes')[0]['id'], 'old workspace')
            staging = stage_import(exported, receiving.root)
            rollback = swap_in_workspace(receiving, staging)
            self.assertTrue(rollback.is_dir())
            self.assertEqual(receiving.setting('language'), 'ja')
            loaded = receiving.one("SELECT id,description,color FROM cards WHERE title='Important task'")
            self.assertEqual(loaded['description'], '<b>formatted</b>')
            self.assertEqual(loaded['color'], '#4f98c8')
            self.assertEqual(receiving.card_checks(loaded['id'])[0]['done'], 1)
            f = receiving.card_files(loaded['id'])[0]
            self.assertEqual((receiving.attachments / f['stored_name']).read_text(), 'must survive')
            self.assertTrue(receiving.wallpaper_path().exists())
            self.assertEqual(receiving.verify_integrity(), [])
            db = sqlite3.connect(rollback / 'kanyx.db')
            self.assertEqual(db.execute('SELECT title FROM cards WHERE id=?', (existing_card,)).fetchone()[0], 'old workspace')
            db.close()
            receiving.close()

    def test_bad_checksum_does_not_modify_current_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            s = Store(root)
            target = export_workspace(s, root/'valid.kanyx')
            with zipfile.ZipFile(target) as z:
                content = {name:z.read(name) for name in z.namelist()}
            content['workspace.db'] = b'bad database'
            invalid = root / 'tampered.kanyx'
            with zipfile.ZipFile(invalid,'w') as z:
                for key,data in content.items(): z.writestr(key,data)
            with self.assertRaises(ValueError):
                stage_import(invalid, root)
            self.assertEqual(s.verify_integrity(), [])
            self.assertTrue(s.dbfile.exists())
            s.close()

    def test_traversal_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bad = root / 'bad.kanyx'
            with zipfile.ZipFile(bad, 'w') as z:
                z.writestr('../evil', 'bad')
                z.writestr('manifest.json', '{}')
            with self.assertRaises(ValueError):
                stage_import(bad, root)
            self.assertFalse((root.parent / 'evil').exists())

    def test_sqlite_backups_can_be_created(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(temp)
            backup = store.backup_now()
            self.assertTrue(backup.exists())
            con = sqlite3.connect(backup)
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            con.close()
            store.close()

if __name__ == '__main__': unittest.main()
