import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import Store
from i18n import LANGUAGES, ROWS, TRANSLATIONS, tr, PRIORITIES

class LocalizationTests(unittest.TestCase):
    def test_all_languages_and_translation_rows(self):
        self.assertEqual(set(LANGUAGES), {'en','de','es','fr','ja','ko'})
        self.assertTrue(all(len(row) == 6 and all(row) for row in ROWS))
        self.assertEqual(len(TRANSLATIONS['ja']), len(ROWS))
        self.assertEqual(tr('ja', 'Save'), '保存')
        self.assertEqual(tr('de', 'Save'), 'Speichern')
        self.assertEqual(tr('bad', 'Save'), 'Save')
    def test_language_setting_survives_restart_and_legacy_database(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(d)
            self.assertEqual(store.setting('language','en'), 'en')
            store.set_setting('language','ko')
            store.close()
            reopened = Store(d)
            self.assertEqual(reopened.setting('language','en'), 'ko')
            self.assertEqual(len(reopened.rows('SELECT * FROM boards')), 1)
            reopened.close()
    def test_priority_values_are_stable(self):
        self.assertEqual([code for _,code in PRIORITIES],['Niedrig','Normal','Hoch','Kritisch'])
        for lang in LANGUAGES:
            for key, code in PRIORITIES:
                self.assertTrue(tr(lang,key))
if __name__=='__main__': unittest.main()
