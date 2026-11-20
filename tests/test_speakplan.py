"""Speech plan tests: what is spoken and in which language. Run without NVDA."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'addon/globalPlugins/vocabularySaver/speakplan.py'
spec = importlib.util.spec_from_file_location('vocabulary_speakplan', MODULE)
speakplan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speakplan)


class LanguageCodeTests(unittest.TestCase):
    def test_starter_languages_have_codes(self):
        self.assertEqual(speakplan.language_code('Japanese'), 'ja')
        self.assertEqual(speakplan.language_code('english'), 'en')
        self.assertEqual(speakplan.language_code('Hindi'), 'hi')

    def test_unknown_or_empty_language_gets_no_code(self):
        for name in ['', None, 'Klingon', 'My custom language']:
            with self.subTest(name=name):
                self.assertIsNone(speakplan.language_code(name))


class WordSegmentTests(unittest.TestCase):
    def test_word_tagged_with_language(self):
        self.assertEqual(speakplan.word_segments('学校', '', 'ja'), [('学校', 'ja')])

    def test_reading_follows_the_word(self):
        self.assertEqual(speakplan.word_segments('学校', 'がっこう', 'ja'), [('学校 (がっこう)', 'ja')])

    def test_reading_same_as_word_not_repeated(self):
        self.assertEqual(speakplan.word_segments('がっこう', 'がっこう', 'ja'), [('がっこう', 'ja')])

    def test_speak_reading_off(self):
        self.assertEqual(speakplan.word_segments('学校', 'がっこう', 'ja', False), [('学校', 'ja')])

    def test_no_language_means_untagged_but_reading_still_spoken(self):
        self.assertEqual(speakplan.word_segments('学校', 'がっこう', None), [('学校 (がっこう)', None)])


class EntrySpeechTests(unittest.TestCase):
    def test_full_entry_plan(self):
        entry = {'word': '学校', 'reading': 'がっこう', 'meaning': 'school', 'notes': 'JLPT N5'}
        segments = speakplan.entry_speech_segments(entry, 'ja')
        # Word and reading are the only Japanese-tagged part; meaning and
        # notes stay in the default voice (the learner's own language).
        tagged = [text for text, code in segments if code == 'ja']
        self.assertEqual(tagged, ['学校 (がっこう)'])
        plain = speakplan.plain_text(segments)
        self.assertIn('Word: ', plain)
        self.assertIn('school', plain)
        self.assertIn('JLPT N5', plain)

    def test_notes_omitted_when_empty(self):
        entry = {'word': 'cat', 'reading': '', 'meaning': 'animal', 'notes': ''}
        plain = speakplan.plain_text(speakplan.entry_speech_segments(entry, 'en'))
        self.assertNotIn('notes', plain)

    def test_untagged_entry_is_one_plain_text(self):
        entry = {'word': 'cat', 'reading': '', 'meaning': 'animal', 'notes': ''}
        segments = speakplan.entry_speech_segments(entry, None)
        self.assertTrue(all(code is None for _, code in segments))


class QuestionSpeechTests(unittest.TestCase):
    def test_question_word_tagged(self):
        segments = speakplan.question_segments(0, 5, '学校', 'がっこう', 'ja')
        self.assertEqual(segments[0], ('Question 1 of 5. What is the meaning of ', None))
        self.assertEqual(segments[1], ('学校 (がっこう)', 'ja'))
        self.assertEqual(segments[-1], ('?', None))


if __name__ == '__main__':
    unittest.main()
