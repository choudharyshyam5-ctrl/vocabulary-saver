"""AI check export/reply tests. Run without NVDA or any network."""
import importlib.util
import json
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'addon/globalPlugins/vocabularySaver/ai_check.py'
spec = importlib.util.spec_from_file_location('vocabulary_ai_check', MODULE)
ai_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai_check)


def data():
    return {
        'schemaVersion': 3,
        'languages': [{'id': 'lang-1', 'name': 'Japanese', 'custom': False}],
        'lessons': [{'id': 'lesson-1', 'name': 'Lesson 1', 'languageId': 'lang-1', 'level': '', 'entries': [
            {'id': 'entry-1', 'word': '学校', 'meaning': 'skool', 'notes': 'keep me', 'reading': ''},
            {'id': 'entry-2', 'word': 'cat', 'meaning': 'an animal', 'notes': '', 'reading': ''},
        ]}],
    }


def reply_payload(reading='がっこう', meaning='school', extra=None):
    lesson = {'lessonId': 'lesson-1', 'entries': [
        {'entryId': 'entry-1', 'word': '学校', 'reading': reading, 'meaning': meaning},
        {'entryId': 'entry-2', 'word': 'cat', 'reading': '', 'meaning': 'an animal'},
    ]}
    if extra:
        lesson.update(extra)
    return {'vocabularySaverAiCheck': 1, 'lessons': [lesson]}


class ExportTests(unittest.TestCase):
    def test_export_contains_prompt_and_all_entries(self):
        text = ai_check.build_ai_export(data())
        self.assertIn('hiragana only', text)
        self.assertIn('"vocabularySaverAiCheck": 1', text)
        self.assertIn('学校', text)
        self.assertIn('entry-1', text)
        self.assertIn('skool', text)
        self.assertIn('Japanese', text)  # Lesson language is named for the AI.

    def test_export_json_is_valid_and_notes_are_not_sent(self):
        text = ai_check.build_ai_export(data())
        payload = json.loads(text.split('JSON to correct:\n', 1)[1])
        self.assertEqual(payload['lessons'][0]['entries'][0]['word'], '学校')
        self.assertNotIn('keep me', text)  # Notes stay private to the export.

    def test_export_round_trips_through_parse(self):
        text = ai_check.build_ai_export(data())
        result = ai_check.parse_ai_reply(text, data())
        self.assertEqual(result['patches'], [])  # Nothing changed yet.


class ParseTests(unittest.TestCase):
    def test_reading_and_meaning_updates(self):
        result = ai_check.parse_ai_reply(json.dumps(reply_payload()), data())
        self.assertEqual(result['readings'], 1)
        self.assertEqual(result['meanings'], 1)
        self.assertEqual(result['patches'], [
            {'lessonId': 'lesson-1', 'entryId': 'entry-1', 'reading': 'がっこう', 'meaning': 'school'},
        ])

    def test_reply_with_surrounding_text_is_found(self):
        reply = 'Here you go!\n' + json.dumps(reply_payload()) + '\nHope this helps.'
        result = ai_check.parse_ai_reply(reply, data())
        self.assertEqual(result['readings'], 1)

    def test_unknown_ids_are_skipped_not_fatal(self):
        payload = reply_payload()
        payload['lessons'][0]['entries'].append({'entryId': 'made-up', 'word': 'x', 'reading': 'y', 'meaning': 'z'})
        payload['lessons'].append({'lessonId': 'ghost', 'entries': []})
        result = ai_check.parse_ai_reply(json.dumps(payload), data())
        self.assertEqual(result['skipped'], 2)
        self.assertEqual(len(result['patches']), 1)

    def test_word_changes_are_ignored(self):
        payload = reply_payload()
        payload['lessons'][0]['entries'][0]['word'] = 'CHANGED BY AI'
        result = ai_check.parse_ai_reply(json.dumps(payload), data())
        for patch in result['patches']:
            self.assertNotIn('word', patch)

    def test_unchanged_fields_produce_no_patch(self):
        result = ai_check.parse_ai_reply(json.dumps(reply_payload(reading='', meaning='skool')), data())
        self.assertEqual(result['patches'], [])
        self.assertEqual(result['readings'], 0)

    def test_entry_under_wrong_lesson_is_skipped(self):
        payload = reply_payload()
        payload['lessons'][0]['lessonId'] = 'other-lesson'
        # lessonId unknown -> whole lesson skipped.
        result = ai_check.parse_ai_reply(json.dumps(payload), data())
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(result['patches'], [])

    def test_missing_marker_rejected(self):
        with self.assertRaises(ai_check.AICheckError):
            ai_check.parse_ai_reply('{"something": "else"}', data())
        with self.assertRaises(ai_check.AICheckError):
            ai_check.parse_ai_reply('no json here at all', data())

    def test_damaged_json_rejected(self):
        with self.assertRaises(ai_check.AICheckError):
            ai_check.parse_ai_reply('{"vocabularySaverAiCheck": 1, "lessons": [', data())

    def test_wrong_structure_rejected(self):
        with self.assertRaises(ai_check.AICheckError):
            ai_check.parse_ai_reply('{"vocabularySaverAiCheck": 1, "lessons": "nope"}', data())

    def test_oversize_reply_rejected(self):
        with self.assertRaises(ai_check.AICheckError):
            ai_check.parse_ai_reply('x' * (ai_check.MAX_REPLY_BYTES + 1), data())

    def test_field_limits_and_empty_meaning_rejected(self):
        with self.assertRaises(ai_check.AICheckError):
            ai_check.parse_ai_reply(json.dumps(reply_payload(reading='x' * 201)), data())
        with self.assertRaises(ai_check.AICheckError):
            ai_check.parse_ai_reply(json.dumps(reply_payload(meaning='')), data())


if __name__ == '__main__':
    unittest.main()
