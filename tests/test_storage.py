"""Run without NVDA: python -m unittest discover -s tests -v."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'addon/globalPlugins/vocabularySaver/storage.py'
spec = importlib.util.spec_from_file_location('vocabulary_storage', MODULE)
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'data/vocabulary.json'
        self.store = storage.Store(self.path)

    def lesson(self):
        return self.store.add_lesson('Lesson 1')

    def populated(self):
        lesson_id = self.lesson()
        entry_id = self.store.put_entry(lesson_id, '猫', 'cat', 'Japanese noun')
        return lesson_id, entry_id

    def test_first_lesson_and_entry_created_together(self):
        lesson_id, entry_id = self.store.add_lesson_with_entry('Lesson 1', '猫', 'cat', '')
        self.assertEqual(self.store.lessons[0]['id'], lesson_id)
        self.assertEqual(self.store.lessons[0]['entries'][0]['id'], entry_id)
        self.assertEqual(storage.Store(self.path).data, self.store.data)

    def test_invalid_first_entry_creates_no_lesson(self):
        with self.assertRaises(storage.DataError):
            self.store.add_lesson_with_entry('Lesson 1', '', 'cat', '')
        self.assertEqual(self.store.lessons, [])
        self.assertFalse(self.path.exists())

    def test_initial_state_not_written_until_change(self):
        self.assertEqual(self.store.lessons, [])
        self.assertFalse(self.path.exists())

    def test_unicode_round_trip(self):
        self.populated()
        self.assertEqual(storage.Store(self.path).data, self.store.data)
        self.assertIn('猫', self.path.read_text(encoding='utf-8'))

    def test_duplicate_lesson_case_insensitive(self):
        self.lesson()
        with self.assertRaises(storage.DataError):
            self.store.add_lesson(' LESSON 1 ')
        self.assertEqual(len(self.store.lessons), 1)

    def test_required_fields(self):
        lesson = self.lesson()
        for word, meaning in [('', 'meaning'), ('word', '')]:
            with self.subTest(word=word), self.assertRaises(storage.DataError):
                self.store.put_entry(lesson, word, meaning, '')

    def test_optional_notes(self):
        self.store.put_entry(self.lesson(), 'word', 'meaning', '')

    def test_edit_and_delete(self):
        lesson, entry = self.populated()
        self.store.put_entry(lesson, '犬', 'dog', '', entry)
        self.assertEqual(self.store.lessons[0]['entries'][0]['word'], '犬')
        self.store.delete_entry(lesson, entry)
        self.assertEqual(self.store.lessons[0]['entries'], [])

    def test_unknown_ids_do_not_write(self):
        self.populated()
        before = self.path.read_bytes()
        with self.assertRaises(storage.DataError):
            self.store.put_entry('missing', 'word', 'meaning', '')
        self.assertEqual(before, self.path.read_bytes())

    def test_lessons_are_copies(self):
        self.lesson()
        self.store.lessons[0]['name'] = 'mutated'
        self.assertEqual(self.store.lessons[0]['name'], 'Lesson 1')

    def test_export_and_import_replace(self):
        self.populated()
        destination = Path(self.directory.name) / 'backup.json'
        self.store.export(destination)
        self.store.add_lesson('Lesson 2')
        self.store.import_replace(destination)
        self.assertEqual(len(self.store.lessons), 1)
        before_import = storage.read_json(self.path.with_suffix('.before-import.json'))
        self.assertEqual(len(before_import['lessons']), 2)

    def test_import_bad_file_preserves_current(self):
        self.populated()
        before = self.path.read_bytes()
        source = Path(self.directory.name) / 'bad.json'
        source.write_text('{not json}', encoding='utf-8')
        with self.assertRaises(storage.DataError):
            self.store.import_replace(source)
        self.assertEqual(before, self.path.read_bytes())

    def test_corrupt_existing_file_not_overwritten(self):
        self.path.parent.mkdir()
        self.path.write_text('broken', encoding='utf-8')
        with self.assertRaises(storage.DataError):
            storage.Store(self.path)
        self.assertEqual(self.path.read_text(), 'broken')

    def test_previous_snapshot(self):
        self.populated()
        previous = copy.deepcopy(self.store.data)
        self.store.add_lesson('Lesson 2')
        self.assertEqual(storage.read_json(self.path.with_suffix('.previous.json')), previous)

    def test_write_failure_preserves_memory_and_file(self):
        self.populated()
        before = copy.deepcopy(self.store.data)
        raw = self.path.read_bytes()
        with patch.object(storage.os, 'replace', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                self.store.add_lesson('Lesson 2')
        self.assertEqual(self.store.data, before)
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])

    def test_internal_export_paths_rejected(self):
        self.populated()
        for suffix in ['.json', '.previous.json', '.before-import.json']:
            with self.subTest(suffix=suffix), self.assertRaises(storage.DataError):
                self.store.export(self.path.with_suffix(suffix))

    def test_duplicate_json_keys_rejected(self):
        self.path.parent.mkdir()
        self.path.write_text('{"schemaVersion":1,"schemaVersion":1,"lessons":[]}', encoding='utf-8')
        with self.assertRaises(storage.DataError):
            storage.read_json(self.path)

    def test_schema_rejects_unknown_keys_types_and_version(self):
        for data in [[], {'schemaVersion': True, 'lessons': []}, {'schemaVersion': 2, 'lessons': []}, {'schemaVersion': 1, 'lessons': [], 'extra': 0}, {'schemaVersion': 1, 'lessons': 'bad'}]:
            with self.subTest(data=data), self.assertRaises(storage.DataError):
                storage.validate(data)

    def test_limits_and_null(self):
        lesson = self.lesson()
        for word in ['x' * 201, 'bad\x00word']:
            with self.subTest(word=word), self.assertRaises(storage.DataError):
                self.store.put_entry(lesson, word, 'meaning', '')

    def test_duplicate_identifiers(self):
        self.populated()
        data = copy.deepcopy(self.store.data)
        data['lessons'][0]['entries'][0]['id'] = data['lessons'][0]['id']
        with self.assertRaises(storage.DataError):
            storage.validate(data)

    def test_oversize_import(self):
        source = Path(self.directory.name) / 'huge.json'
        source.write_bytes(b' ' * (storage.MAX_FILE_BYTES + 1))
        with self.assertRaises(storage.DataError):
            self.store.import_replace(source)

    def test_bom_import(self):
        source = Path(self.directory.name) / 'bom.json'
        source.write_bytes(b'\xef\xbb\xbf' + json.dumps(self.store.data).encode())
        self.store.import_replace(source)


if __name__ == '__main__':
    unittest.main()
