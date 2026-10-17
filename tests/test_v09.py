"""Visual preferences are ordinary, portable, persisted workspace settings."""
import tempfile
import unittest
from pathlib import Path
from db import Store
from i18n import tr, LANGUAGES


class PreferencesTests(unittest.TestCase):
    def test_visual_settings_persist_across_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder))
            for k, v in [('wallpaper_brightness', '67'), ('column_opacity', '74'), ('ui_scale', '120')]:
                store.set_setting(k, v)
            store.close()
            store = Store(Path(folder))
            self.assertEqual(store.setting('wallpaper_brightness'), '67')
            self.assertEqual(store.setting('column_opacity'), '74')
            self.assertEqual(store.setting('ui_scale'), '120')
            store.close()

    def test_appearance_translations(self):
        for code in LANGUAGES:
            for term in ('Appearance', 'Wallpaper brightness', 'Column opacity', 'Interface scale'):
                self.assertTrue(tr(code, term))
