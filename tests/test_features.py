import tempfile
import unittest
from pathlib import Path
from db import Store


class NewFeaturesTests(unittest.TestCase):
    def test_column_reorder_persists(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(temp)
            board = store.rows('SELECT id FROM boards')[0]['id']
            original = [r['id'] for r in store.rows('SELECT id FROM lanes WHERE board_id=? ORDER BY position,id', (board,))]
            store.move_lane(original[0], 2)
            ordered = [r['id'] for r in store.rows('SELECT id FROM lanes WHERE board_id=? ORDER BY position,id', (board,))]
            self.assertEqual(ordered, [original[1], original[2], original[0]])
            store.move_lane(original[2], -10)
            ordered = [r['id'] for r in store.rows('SELECT id FROM lanes WHERE board_id=? ORDER BY position,id', (board,))]
            self.assertEqual(ordered[0], original[2])
            store.close()
            reopened = Store(temp)
            self.assertEqual([r['id'] for r in reopened.rows('SELECT id FROM lanes WHERE board_id=? ORDER BY position,id', (board,))], ordered)
            reopened.close()

    def test_wallpaper_copied_and_clearable(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(temp)
            source = Path(temp) / 'picture.png'
            source.write_bytes(b'example image bytes')
            copied = store.set_wallpaper(source)
            self.assertTrue(copied.exists())
            self.assertEqual(copied.read_bytes(), source.read_bytes())
            self.assertEqual(store.wallpaper_path(), copied)
            store.close()
            reopened = Store(temp)
            self.assertEqual(reopened.wallpaper_path(), copied)
            reopened.clear_wallpaper()
            self.assertIsNone(reopened.wallpaper_path())
            self.assertFalse(copied.exists())
            reopened.close()

if __name__ == '__main__':
    unittest.main()
