"""Japanese script detection and kana-to-romaji tests. Run without NVDA."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'addon/globalPlugins/vocabularySaver/romaji.py'
spec = importlib.util.spec_from_file_location('vocabulary_romaji_readings', MODULE)
romaji = importlib.util.module_from_spec(spec)
spec.loader.exec_module(romaji)


class ScriptDetectionTests(unittest.TestCase):
    def test_has_japanese_script(self):
        for text in ['学校', 'がっこう', 'ガッコウ', 'ｶﾀｶﾅ', 'study 日本語']:
            with self.subTest(text=text):
                self.assertTrue(romaji.has_japanese_script(text))
        for text in ['school', 'gakkou', '123', 'École française', '']:
            with self.subTest(text=text):
                self.assertFalse(romaji.has_japanese_script(text))

    def test_has_kanji(self):
        self.assertTrue(romaji.has_kanji('学校'))
        self.assertTrue(romaji.has_kanji('がっこう学校'))
        self.assertFalse(romaji.has_kanji('がっこう'))
        self.assertFalse(romaji.has_kanji('school'))

    def test_detect_lookup_language_script_wins(self):
        # Kanji/kana search Japanese no matter what the lesson language is.
        self.assertEqual(romaji.detect_lookup_language('学校', 'English'), 'japanese')
        self.assertEqual(romaji.detect_lookup_language('がっこう', 'Korean'), 'japanese')
        self.assertEqual(romaji.detect_lookup_language('学校', ''), 'japanese')

    def test_detect_lookup_language_latin_letters(self):
        # Plain letters: English everywhere except inside a Japanese lesson,
        # where they are romaji and try the Japanese dictionary first.
        self.assertEqual(romaji.detect_lookup_language('school', 'English'), 'english')
        self.assertEqual(romaji.detect_lookup_language('school', ''), 'english')
        self.assertEqual(romaji.detect_lookup_language('school', 'Hindi'), 'english')
        self.assertEqual(romaji.detect_lookup_language('gakkou', 'Japanese'), 'japanese')
        self.assertEqual(romaji.detect_lookup_language('gakkou', 'japanese'), 'japanese')


class ToRomajiTests(unittest.TestCase):
    def test_basic_words(self):
        for kana, expected in [
            ('がっこう', 'gakkou'), ('がくせい', 'gakusei'), ('せんせい', 'sensei'),
            ('する', 'suru'), ('きょう', 'kyou'), ('しんぶん', 'shinbun'),
            ('おおきい', 'ookii'), ('ちず', 'chizu'), ('じゃ', 'ja'),
        ]:
            with self.subTest(kana=kana):
                self.assertEqual(romaji.to_romaji(kana), expected)

    def test_katakana_converts_like_hiragana(self):
        self.assertEqual(romaji.to_romaji('ガッコウ'), 'gakkou')
        self.assertEqual(romaji.to_romaji('ケーキ'), 'ke-ki')  # Long-vowel mark is a hyphen.

    def test_mixed_content_passes_through(self):
        self.assertEqual(romaji.to_romaji('学校がっこう'), '学校gakkou')  # Kanji stay as they are.
        self.assertEqual(romaji.to_romaji('JLPT がっこう 2'), 'JLPT gakkou 2')
        self.assertEqual(romaji.to_romaji(''), '')
        self.assertEqual(romaji.to_romaji('school'), 'school')

    def test_round_trip_with_forward_table(self):
        for kana in ['がっこう', 'きょう', 'せんせい', 'しんぶん', 'ちいさい']:
            with self.subTest(kana=kana):
                self.assertEqual(romaji.to_hiragana(romaji.to_romaji(kana)), kana)


if __name__ == '__main__':
    unittest.main()
