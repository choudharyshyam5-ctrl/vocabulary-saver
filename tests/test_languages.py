"""Language organization tests. Run without NVDA: python -m unittest discover -s tests -v."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'addon/globalPlugins/vocabularySaver/storage.py'
spec = importlib.util.spec_from_file_location('vocabulary_storage_languages', MODULE)
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)


def v1_file(path, entries=None):
    path.write_text(json.dumps({
        'schemaVersion': 1,
        'lessons': [{'id': 'lesson-1', 'name': 'Lesson 1', 'entries': entries or [
            {'id': 'entry-1', 'word': '猫', 'meaning': 'cat', 'notes': 'Japanese noun'},
        ]}],
    }), encoding='utf-8')


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'data/vocabulary.json'
        self.path.parent.mkdir()

    def test_v1_file_migrates_with_lessons_unassigned(self):
        v1_file(self.path)
        store = storage.Store(self.path)
        self.assertEqual(store.data['schemaVersion'], 3)
        lesson = store.lessons[0]
        self.assertIsNone(lesson['languageId'])
        self.assertEqual(lesson['level'], '')
        self.assertEqual(lesson['entries'][0]['word'], '猫')
        self.assertEqual(lesson['entries'][0]['reading'], '')

    def test_migration_adds_starter_languages(self):
        v1_file(self.path)
        store = storage.Store(self.path)
        names = [x['name'] for x in store.languages]
        self.assertEqual(names, list(storage.STARTER_LANGUAGES))
        self.assertTrue(all(x['custom'] is False for x in store.languages))

    def test_migration_does_not_rewrite_file_until_change(self):
        v1_file(self.path)
        before = self.path.read_bytes()
        storage.Store(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_first_change_after_migration_keeps_data_in_snapshot(self):
        v1_file(self.path)
        store = storage.Store(self.path)
        store.add_lesson('Lesson 2')
        previous = storage.read_json(self.path.with_suffix('.previous.json'))
        self.assertEqual(previous['lessons'][0]['entries'][0]['meaning'], 'cat')
        current = storage.read_json(self.path)
        self.assertEqual(len(current['lessons']), 2)
        self.assertEqual(current['lessons'][0]['entries'][0]['word'], '猫')

    def test_v1_import_accepted(self):
        store = storage.Store(self.path)
        store.add_lesson('Existing')
        source = Path(self.directory.name) / 'old-backup.json'
        v1_file(source)
        store.import_replace(source)
        self.assertEqual(store.lessons[0]['name'], 'Lesson 1')
        self.assertIsNone(store.lessons[0]['languageId'])

    def test_unknown_future_version_rejected(self):
        self.path.write_text(json.dumps({'schemaVersion': 4, 'languages': [], 'lessons': []}), encoding='utf-8')
        with self.assertRaises(storage.DataError):
            storage.Store(self.path)
        self.assertEqual(json.loads(self.path.read_text())['schemaVersion'], 4)


def v2_file(path, entries=None):
    path.write_text(json.dumps({
        'schemaVersion': 2,
        'languages': [{'id': 'lang-1', 'name': 'Japanese', 'custom': False}],
        'lessons': [{'id': 'lesson-1', 'name': 'Lesson 1', 'languageId': 'lang-1', 'level': '', 'entries': entries or [
            {'id': 'entry-1', 'word': '学校', 'meaning': 'school', 'notes': 'Japanese noun'},
        ]}],
    }), encoding='utf-8')


class V2MigrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'data/vocabulary.json'
        self.path.parent.mkdir()

    def backup_path(self):
        return self.path.with_suffix('.v2-backup.json')

    def test_v2_file_gains_empty_readings(self):
        v2_file(self.path)
        store = storage.Store(self.path)
        self.assertEqual(store.data['schemaVersion'], 3)
        entry = store.lessons[0]['entries'][0]
        self.assertEqual(entry['word'], '学校')
        self.assertEqual(entry['reading'], '')
        self.assertFalse(self.backup_path().exists())  # No write, no backup yet.

    def test_first_write_after_v2_migration_saves_v2_backup(self):
        v2_file(self.path)
        original = json.loads(self.path.read_text(encoding='utf-8'))
        store = storage.Store(self.path)
        store.add_lesson('Lesson 2')
        self.assertEqual(json.loads(self.backup_path().read_text(encoding='utf-8')), original)

    def test_restore_v2_backup_rolls_back(self):
        v2_file(self.path)
        store = storage.Store(self.path)
        store.add_lesson('Lesson 2')
        restored = json.loads(self.backup_path().read_text(encoding='utf-8'))
        self.path.write_text(json.dumps(restored), encoding='utf-8')
        rolled_back = storage.Store(self.path)
        self.assertEqual([x['name'] for x in rolled_back.lessons], ['Lesson 1'])
        self.assertEqual(rolled_back.lessons[0]['entries'][0]['word'], '学校')

    def test_export_to_v2_backup_path_rejected(self):
        v2_file(self.path)
        store = storage.Store(self.path)
        store.add_lesson('Lesson 2')
        with self.assertRaises(storage.DataError):
            store.export(self.backup_path())


class LanguageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'data/vocabulary.json'
        self.store = storage.Store(self.path)

    def test_new_store_seeds_starter_languages_without_writing(self):
        self.assertEqual([x['name'] for x in self.store.languages], list(storage.STARTER_LANGUAGES))
        self.assertFalse(self.path.exists())

    def test_add_language_custom_and_dedupe(self):
        identifier = self.store.add_language('Hindi')
        language = next(x for x in self.store.languages if x['id'] == identifier)
        self.assertTrue(language['custom'])
        with self.assertRaises(storage.DataError):
            self.store.add_language(' hindi ')
        with self.assertRaises(storage.DataError):
            self.store.add_language('Japanese')

    def test_rename_language(self):
        identifier = self.store.add_language('Hindi')
        self.store.rename_language(identifier, 'Hindi (Devanagari)')
        self.assertEqual(next(x for x in self.store.languages if x['id'] == identifier)['name'], 'Hindi (Devanagari)')
        with self.assertRaises(storage.DataError):
            self.store.rename_language(identifier, 'Japanese')

    def test_delete_language_only_when_unused(self):
        identifier = self.store.add_language('Hindi')
        lesson = self.store.add_lesson('Lesson 1', language_id=identifier)
        with self.assertRaises(storage.DataError):
            self.store.delete_language(identifier)
        self.store.set_lesson_language(lesson, None)
        self.store.delete_language(identifier)
        self.assertNotIn('Hindi', [x['name'] for x in self.store.languages])

    def test_assign_and_unassign_lesson_language(self):
        lesson = self.store.add_lesson('Lesson 1')
        self.assertIsNone(self.store.lessons[0]['languageId'])
        language = self.store.languages[0]['id']
        self.store.set_lesson_language(lesson, language)
        self.assertEqual(self.store.lessons[0]['languageId'], language)
        self.store.set_lesson_language(lesson, None)
        self.assertIsNone(self.store.lessons[0]['languageId'])

    def test_unknown_language_rejected(self):
        lesson = self.store.add_lesson('Lesson 1')
        for action in [lambda: self.store.set_lesson_language(lesson, 'missing'),
                       lambda: self.store.add_lesson('X', language_id='missing')]:
            with self.assertRaises(storage.DataError):
                action()

    def test_lesson_level_free_text(self):
        lesson = self.store.add_lesson('Lesson 1')
        self.store.set_lesson_level(lesson, 'JLPT N5')
        self.assertEqual(self.store.lessons[0]['level'], 'JLPT N5')
        self.store.set_lesson_level(lesson, '')
        self.assertEqual(self.store.lessons[0]['level'], '')

    def test_new_lesson_with_language_and_level(self):
        language = self.store.languages[0]['id']
        lesson = self.store.add_lesson('Minna 1', language_id=language, level='JLPT N5')
        self.assertEqual(self.store.lessons[0]['languageId'], language)
        self.assertEqual(self.store.lessons[0]['level'], 'JLPT N5')
        lesson2, entry = self.store.add_lesson_with_entry('Minna 2', '犬', 'dog', '', language_id=language, level='JLPT N5')
        self.assertEqual(self.store.lessons[1]['languageId'], language)

    def test_file_with_unknown_language_reference_rejected(self):
        self.store.add_lesson('Lesson 1')
        self.path.write_text(json.dumps({
            'schemaVersion': 2,
            'languages': [{'id': 'a', 'name': 'Japanese', 'custom': False}],
            'lessons': [{'id': 'l', 'name': 'L', 'languageId': 'missing', 'level': '', 'entries': []}],
        }), encoding='utf-8')
        with self.assertRaises(storage.DataError):
            storage.Store(self.path)

    def test_export_import_v2_round_trip(self):
        language = self.store.languages[0]['id']
        lesson = self.store.add_lesson('Minna 1', language_id=language, level='JLPT N5')
        self.store.put_entry(lesson, '猫', 'cat', '')
        destination = Path(self.directory.name) / 'backup.json'
        self.store.export(destination)
        self.store.add_language('Hindi')
        self.store.import_replace(destination)
        self.assertNotIn('Hindi', [x['name'] for x in self.store.languages])
        self.assertEqual(self.store.lessons[0]['languageId'], language)
        self.assertEqual(self.store.lessons[0]['level'], 'JLPT N5')

    def test_languages_are_copies(self):
        self.store.languages[0]['name'] = 'mutated'
        self.assertEqual(self.store.languages[0]['name'], 'Japanese')


if __name__ == '__main__':
    unittest.main()


class RollbackBackupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'data/vocabulary.json'
        self.path.parent.mkdir()
        self.original = {
            'schemaVersion': 1,
            'lessons': [{'id': 'lesson-1', 'name': 'Lesson 1', 'entries': [
                {'id': 'entry-1', 'word': '猫', 'meaning': 'cat', 'notes': 'Japanese noun'},
            ]}],
        }
        self.path.write_text(json.dumps(self.original), encoding='utf-8')

    def backup_path(self):
        return self.path.with_suffix('.v1-backup.json')

    def test_first_write_creates_exact_v1_backup(self):
        store = storage.Store(self.path)
        self.assertFalse(self.backup_path().exists())
        store.add_lesson('Lesson 2')
        self.assertEqual(json.loads(self.backup_path().read_text(encoding='utf-8')), self.original)

    def test_backup_survives_many_later_writes(self):
        store = storage.Store(self.path)
        store.add_lesson('Lesson 2')
        before = self.backup_path().read_bytes()
        for index in range(3, 8):
            store.add_lesson(f'Lesson {index}')
        store.put_entry('lesson-1', '犬', 'dog', '')
        self.assertEqual(self.backup_path().read_bytes(), before)

    def test_restore_v1_backup_rolls_back(self):
        store = storage.Store(self.path)
        store.add_lesson('Lesson 2')
        # Simulated downgrade: restore the v1 backup as the live file, old schema reads cleanly.
        restored = json.loads(self.backup_path().read_text(encoding='utf-8'))
        self.path.write_text(json.dumps(restored), encoding='utf-8')
        rolled_back = storage.Store(self.path)
        self.assertEqual([x['name'] for x in rolled_back.lessons], ['Lesson 1'])
        self.assertEqual(rolled_back.lessons[0]['entries'][0]['word'], '猫')

    def test_backup_not_created_for_v2_files(self):
        store = storage.Store(self.path)
        store.add_lesson('Lesson 2')
        backup = self.backup_path().read_bytes()
        fresh = storage.Store(self.path)
        fresh.add_lesson('Lesson 3')
        self.assertEqual(self.backup_path().read_bytes(), backup)

    def test_export_to_backup_path_rejected(self):
        store = storage.Store(self.path)
        store.add_lesson('Lesson 2')
        with self.assertRaises(storage.DataError):
            store.export(self.backup_path())
