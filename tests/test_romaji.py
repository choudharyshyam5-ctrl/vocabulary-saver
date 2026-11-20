"""Romaji-to-hiragana tests. Run without NVDA: python -m unittest discover -s tests -v.

Covers the whole-field conversion, the exact per-keystroke EVT_TEXT sequence
through the ConversionSession adapter the dialog uses, and deterministic undo.
"""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'addon/globalPlugins/vocabularySaver/romaji.py'
spec = importlib.util.spec_from_file_location('vocabulary_romaji', MODULE)
romaji = importlib.util.module_from_spec(spec)
spec.loader.exec_module(romaji)


def type_text(text):
    """Simulate the dialog: user_edit after every typed char, then user_finalize on blur."""
    session = romaji.ConversionSession()
    states = []
    for char in text:
        states.append(session.user_edit(session.field + char))
    return states, session.user_finalize()


class ToHiraganaTests(unittest.TestCase):
    def test_common_words(self):
        for romaji_text, expected in [
            ('watashi', 'わたし'), ('gakkou', 'がっこう'), ('sensei', 'せんせい'),
            ('shinbun', 'しんぶん'), ('genki', 'げんき'), ('onna', 'おんな'),
            ('kyou', 'きょう'), ('gakusei', 'がくせい'), ('kitte', 'きって'),
            ('zasshi', 'ざっし'), ('neko', 'ねこ'), ('chan', 'ちゃん'),
        ]:
            with self.subTest(romaji=romaji_text):
                self.assertEqual(romaji.to_hiragana(romaji_text), expected)

    def test_phonetic_kana_not_dictionary(self):
        # Pure transliteration: no dictionary, so particle words render phonetically.
        self.assertEqual(romaji.to_hiragana('konnichiwa'), 'こんにちわ')
        self.assertEqual(romaji.to_hiragana('konnichiha'), 'こんにちは')

    def test_apostrophe_is_syllabic_n_delimiter_and_consumed(self):
        # kin'you must be きんよう, not きにょう; the delimiter never lands in the word.
        self.assertEqual(romaji.to_hiragana("kin'you"), 'きんよう')
        self.assertEqual(romaji.to_hiragana("ten'i"), 'てんい')
        self.assertEqual(romaji.to_hiragana("n'"), 'ん')
        self.assertEqual(romaji.to_hiragana('kinyou'), 'きにょう')  # without the delimiter
        # Only a romaji run ending in n consumes the delimiter; a user-typed
        # kana ん keeps its apostrophe exactly as entered.
        self.assertEqual(romaji.to_hiragana("かん'you"), "かん'よう")
        self.assertEqual(romaji.to_hiragana("かん'"), "かん'")

    def test_trailing_n_waits_while_typing(self):
        self.assertEqual(romaji.to_hiragana('shinbun', final=False), 'しんぶn')
        self.assertEqual(romaji.to_hiragana('chan', final=False), 'ちゃn')
        self.assertEqual(romaji.to_hiragana('chan', final=True), 'ちゃん')

    def test_run_before_break_is_complete(self):
        self.assertEqual(romaji.to_hiragana('gomen nasai', final=False), 'ごめん なさい')
        self.assertEqual(romaji.to_hiragana('neko ga suki', final=False), 'ねこ が すき')

    def test_existing_japanese_untouched(self):
        for already in ['わたし', 'かんじ', '私', 'カタカナ', '日本語のテスト']:
            with self.subTest(text=already):
                self.assertEqual(romaji.to_hiragana(already), already)

    def test_mixed_case_and_acronyms_untouched(self):
        for text in ['Tokyo', 'Watashi', 'JLPT N5', 'N5']:
            with self.subTest(text=text):
                self.assertEqual(romaji.to_hiragana(text), text)

    def test_non_romaji_runs_never_half_converted_on_paste_or_blur(self):
        # Whole-field policy: a run with any invalid romaji letter stays as typed.
        for text in ['max', 'juice', 'extra', 'love', 'quiz']:
            with self.subTest(text=text):
                self.assertEqual(romaji.to_hiragana(text), text)
                self.assertEqual(romaji.to_hiragana(text, final=False), text)

    def test_mixed_script_partial_conversion(self):
        self.assertEqual(romaji.to_hiragana('かんji'), 'かんじ')

    def test_empty_and_punctuation(self):
        self.assertEqual(romaji.to_hiragana(''), '')
        self.assertEqual(romaji.to_hiragana('123 !?'), '123 !?')


class IncrementalTypingTests(unittest.TestCase):
    """The dialog runs ConversionSession.user_edit on every EVT_TEXT; test that adapter."""

    def test_typing_sequences_reach_correct_final(self):
        for word, expected in [
            ('watashi', 'わたし'), ('gakkou', 'がっこう'), ('konnichiha', 'こんにちは'),
            ('shinbun', 'しんぶん'), ('nna', 'んな'), ("n'", 'ん'),
            ('sensei', 'せんせい'), ('gomen nasai', 'ごめん なさい'), ("kin'you", 'きんよう'),
        ]:
            with self.subTest(word=word):
                _, final = type_text(word)
                self.assertEqual(final, expected)

    def test_intermediate_states_known_for_tricky_words(self):
        states, _ = type_text('gakkou')
        self.assertEqual(states, ['g', 'が', 'がk', 'がkk', 'がっこ', 'がっこう'])
        states, _ = type_text('shinbun')
        self.assertEqual(states, ['s', 'sh', 'し', 'しn', 'しnb', 'しんぶ', 'しんぶn'])
        states, _ = type_text('nna')
        self.assertEqual(states, ['n', 'んn', 'んな'])

    def test_non_romaji_words_typed_letter_by_letter(self):
        # Words that do not begin as romaji never convert; IME-like note: a word
        # that starts as valid romaji converts before later letters arrive,
        # exactly like Windows IME, and the dialog's Undo button restores it.
        _, final = type_text('skype')
        self.assertEqual(final, 'skype')
        states, _ = type_text('max')
        self.assertEqual(states[-1], 'まx')  # documented IME-like behavior, undoable in the dialog
        states, _ = type_text('Tokyo')
        self.assertEqual(states[-1], 'Tokyo')

    def test_paste_converts_whole_word_at_once(self):
        session = romaji.ConversionSession()
        self.assertEqual(session.user_edit('arigatou'), 'ありがとう')
        session = romaji.ConversionSession()
        self.assertEqual(session.user_edit('ohayou gozaimasu'), 'おはよう ございます')

    def test_ime_supplied_kana_passthrough_while_typing(self):
        # With a system IME active the field receives kana; reconversion must be a no-op.
        states, final = type_text('わたし')
        self.assertEqual(states, ['わ', 'わた', 'わたし'])
        self.assertEqual(final, 'わたし')

    def test_checkbox_off_tracks_without_converting(self):
        session = romaji.ConversionSession()
        for char in 'watashi':
            session.user_edit(session.field + char, convert=False)
        self.assertEqual(session.field, 'watashi')
        # Re-enabling conversion converts the existing field on blur.
        self.assertEqual(session.user_finalize(), 'わたし')


class UndoTests(unittest.TestCase):
    """Deterministic undo: exact raw romaji when input was simple typing/paste,
    exact one-step pre-conversion text after edits that break raw tracking."""

    def test_undo_restores_exact_raw_romaji_after_typing(self):
        session = romaji.ConversionSession()
        for char in 'watashi':
            session.user_edit(session.field + char)
        self.assertEqual(session.field, 'わたし')
        restored, was_raw = session.undo()
        self.assertEqual((restored, was_raw), ('watashi', True))

    def test_undo_restores_exact_raw_romaji_after_paste(self):
        session = romaji.ConversionSession()
        session.user_edit('konnichiha')
        session.user_finalize()
        self.assertEqual(session.field, 'こんにちは')
        restored, was_raw = session.undo()
        self.assertEqual((restored, was_raw), ('konnichiha', True))

    def test_undo_after_deletion_falls_back_to_one_step(self):
        session = romaji.ConversionSession()
        for char in 'watashi':
            session.user_edit(session.field + char)
        session.user_edit(session.field[:-1])   # user deletes the last kana
        session.user_edit(session.field + 'shi')
        self.assertEqual(session.field, 'わたし')
        restored, was_raw = session.undo()
        self.assertEqual((restored, was_raw), ('わたshi', False))

    def test_undo_restores_live_typed_max(self):
        session = romaji.ConversionSession()
        for char in 'max':
            session.user_edit(session.field + char)
        self.assertEqual(session.field, 'まx')
        restored, was_raw = session.undo()
        self.assertEqual((restored, was_raw), ('max', True))

    def test_undo_is_inert_without_conversion(self):
        session = romaji.ConversionSession()
        for char in 'わたし':
            session.user_edit(session.field + char)
        self.assertEqual(session.undo(), ('わたし', False))

    def test_undo_is_single_use(self):
        session = romaji.ConversionSession()
        for char in 'neko':
            session.user_edit(session.field + char)
        first = session.undo()
        self.assertEqual(first, ('neko', True))
        self.assertEqual(session.undo(), ('neko', False))

    def test_existing_word_edits_undo_one_step(self):
        # Editing an already-saved word cannot reconstruct raw romaji.
        session = romaji.ConversionSession('dog')
        session.user_edit('dogs')
        session.user_finalize()
        restored, was_raw = session.undo()
        self.assertEqual((restored, was_raw), ('dogs', False))


if __name__ == '__main__':
    unittest.main()
