"""Dictionary lookup tests - fully offline against recorded API responses.

Recorded samples in tests/samples were captured from the live services on
2 Nov 2026 (Jisho words, Tatoeba sentences, dictionaryapi.dev English).
"""
import importlib.util
import json
from pathlib import Path
import urllib.error
import unittest

BASE = Path(__file__).resolve().parents[1]
MODULE = BASE / 'addon/globalPlugins/vocabularySaver/dict_lookup.py'
spec = importlib.util.spec_from_file_location('vocabulary_dict_lookup', MODULE)
dict_lookup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dict_lookup)

SAMPLES = BASE / 'tests/samples'


def sample(name):
    return json.loads((SAMPLES / name).read_text(encoding='utf-8'))


class UrlTests(unittest.TestCase):
    def test_urls_are_encoded(self):
        self.assertEqual(dict_lookup.jisho_url('gakkou'), 'https://jisho.org/api/v1/search/words?keyword=gakkou')
        self.assertEqual(dict_lookup.tatoeba_url('学校'), 'https://tatoeba.org/en/api_v0/search?from=jpn&to=eng&query=%E5%AD%A6%E6%A0%A1')
        self.assertEqual(dict_lookup.tatoeba_url('school', 'eng', 'jpn'), 'https://tatoeba.org/en/api_v0/search?from=eng&to=jpn&query=school')
        self.assertEqual(dict_lookup.english_url(' School '), 'https://api.dictionaryapi.dev/api/v2/entries/en/school')


class ParseJishoTests(unittest.TestCase):
    def test_parses_word_reading_meanings_jlpt(self):
        entries = dict_lookup.parse_jisho(sample('jisho_school.json'))
        self.assertTrue(entries)
        first = entries[0]
        self.assertEqual(first['word'], '学校')
        self.assertEqual(first['reading'], 'がっこう')
        self.assertIn('school', first['meanings'][0])
        self.assertEqual(first['jlpt'], 'N5')

    def test_empty_data_is_not_found(self):
        self.assertEqual(dict_lookup.parse_jisho({'data': []}), [])
        with self.assertRaises(dict_lookup.LookupError) as caught:
            dict_lookup.lookup_japanese('zzzzz', fetcher=lambda url: {'data': []})
        self.assertEqual(str(caught.exception), 'not_found')

    def test_kana_only_form_uses_reading_as_word(self):
        payload = {'data': [{'japanese': [{'reading': 'する'}], 'senses': [{'english_definitions': ['to do']}], 'jlpt': []}]}
        entries = dict_lookup.parse_jisho(payload)
        self.assertEqual(entries[0]['word'], 'する')
        self.assertEqual(entries[0]['jlpt'], '')


class ParseTatoebaTests(unittest.TestCase):
    def test_parses_japanese_sentence_with_translation_link_and_license(self):
        examples = dict_lookup.parse_tatoeba(sample('tatoeba_gakkou.json'))
        self.assertTrue(examples)
        first = examples[0]
        self.assertIn('学校', first['text'])
        self.assertEqual(first['lang'], 'jpn')
        self.assertTrue(first['translation_id'])
        self.assertEqual(first['license'], 'CC BY 2.0 FR')
        self.assertEqual(first['id'], 10756861)
        self.assertEqual(first['author'], 'small_snow')

    def test_parses_english_sentences_without_kana_reading(self):
        payload = {'results': [
            {'lang': 'eng', 'text': 'The school is big.', 'id': 42,
             'translations': [[{'lang': 'jpn', 'text': '学校は大きい。', 'id': 43}]],
             'transcriptions': [{'script': 'Hrkt', 'text': 'ignored for English'}],
             'user': {'username': ' CK '}, 'license': 'CC BY 2.0 FR'},
            {'lang': 'jpn', 'text': '日本語の文。', 'id': 44, 'translations': [], 'transcriptions': []},
        ]}
        examples = dict_lookup.parse_tatoeba(payload, 'eng', 'jpn')
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]['text'], 'The school is big.')
        self.assertEqual(examples[0]['reading'], '')
        self.assertEqual(examples[0]['translation_id'], 43)

    def test_lookup_english_examples_uses_english_sentences(self):
        payload = {'results': [{'lang': 'eng', 'text': 'A sentence.', 'id': 1, 'translations': [], 'transcriptions': [], 'user': {}, 'license': 'CC BY 2.0 FR'}]}
        result = dict_lookup.lookup_english_examples('school', fetcher=lambda url: payload)
        self.assertIn('Tatoeba', result['source'])
        self.assertEqual(result['examples'][0]['text'], 'A sentence.')

    def test_attribution_line_carries_author_license_and_link(self):
        example = dict_lookup.parse_tatoeba(sample('tatoeba_gakkou.json'))[0]
        line = dict_lookup.tatoeba_attribution(example)
        self.assertIn('#10756861', line)
        self.assertIn('small_snow', line)
        self.assertIn('CC BY 2.0 FR', line)
        self.assertIn('https://tatoeba.org/en/sentences/show/10756861', line)

    def test_translation_omitted_but_linked_never_misattributed(self):
        example = dict_lookup.parse_tatoeba(sample('tatoeba_gakkou.json'))[0]
        # Saved/displayed example text carries the sentence only.
        self.assertEqual(dict_lookup.tatoeba_example_text(example), example['text'])
        # Attribution links the translation sentence without embedding its text
        # and never credits it to the original sentence's author.
        line = dict_lookup.tatoeba_attribution(example)
        self.assertIn(f"sentences/show/{example['translation_id']}", line)
        self.assertIn('not embedded', line)
        translation_part = line.split('Translation', 1)[1]
        self.assertNotIn('small_snow', translation_part)

    def test_attribution_falls_back_without_id_or_author(self):
        line = dict_lookup.tatoeba_attribution({'text': 'x', 'id': None, 'author': '', 'license': ''})
        self.assertIn('a Tatoeba member', line)
        self.assertIn('CC BY 2.0 FR', line)
        self.assertIn('https://tatoeba.org', line)

    def test_skips_other_languages_and_limits(self):
        payload = {'results': [{'lang': 'eng', 'text': 'School.'}] + [{'lang': 'jpn', 'text': f'文{i}', 'translations': [], 'transcriptions': []} for i in range(10)]}
        examples = dict_lookup.parse_tatoeba(payload, 'jpn', 'eng', limit=3)
        self.assertEqual(len(examples), 3)
        self.assertTrue(all(x['text'].startswith('文') for x in examples))


class ParseEnglishTests(unittest.TestCase):
    def test_parses_meanings_and_inline_examples(self):
        entries = dict_lookup.parse_english(sample('english_school.json'))
        self.assertTrue(entries)
        first = entries[0]
        self.assertEqual(first['word'], 'school')
        self.assertTrue(first['meanings'])
        self.assertTrue(any('(' in m for m in first['meanings']))  # part of speech prefix
        self.assertTrue(first['examples'])

    def test_not_found(self):
        with self.assertRaises(dict_lookup.LookupError) as caught:
            dict_lookup.lookup_english('zzzqqq', fetcher=lambda url: [])
        self.assertEqual(str(caught.exception), 'not_found')


class JishoAttributionTests(unittest.TestCase):
    def test_meaning_attribution_mentions_jisho_jmdict_license(self):
        self.assertIn('Jisho', dict_lookup.JISHI_ATTRIBUTION)
        self.assertIn('JMdict', dict_lookup.JISHI_ATTRIBUTION)
        self.assertIn('CC BY-SA 4.0', dict_lookup.JISHI_ATTRIBUTION)
        self.assertIn('edrdg.org', dict_lookup.JISHI_ATTRIBUTION)


class EnglishAttributionTests(unittest.TestCase):
    def test_license_and_source_preserved(self):
        entry = dict_lookup.parse_english(sample('english_school.json'))[0]
        self.assertEqual(entry['license']['name'], 'CC BY-SA 3.0')
        self.assertTrue(entry['sourceUrls'][0].startswith('https://en.wiktionary.org'))
        line = dict_lookup.english_attribution(entry)
        self.assertIn('CC BY-SA 3.0', line)
        self.assertIn('https://creativecommons.org/licenses/by-sa/3.0', line)
        self.assertIn('en.wiktionary.org/wiki/school', line)

    def test_attribution_tolerates_missing_license(self):
        line = dict_lookup.english_attribution({})
        self.assertIn('dictionaryapi.dev', line)


class ErrorMappingTests(unittest.TestCase):
    """The mapping lives in _fetch_json; patch urlopen to exercise it offline."""

    def _patched(self, error):
        import unittest.mock
        return unittest.mock.patch('urllib.request.urlopen', side_effect=error)

    def test_http_404_maps_to_not_found(self):
        with self._patched(urllib.error.HTTPError('u', 404, 'Not Found', {}, None)):
            with self.assertRaises(dict_lookup.LookupError) as caught:
                dict_lookup._fetch_json('https://example.invalid/x')
        self.assertEqual(str(caught.exception), 'not_found')

    def test_http_500_maps_to_offline(self):
        with self._patched(urllib.error.HTTPError('u', 500, 'Server Error', {}, None)):
            with self.assertRaises(dict_lookup.LookupError) as caught:
                dict_lookup._fetch_json('https://example.invalid/x')
        self.assertEqual(str(caught.exception), 'offline')

    def test_connection_failure_maps_to_offline(self):
        with self._patched(urllib.error.URLError('no route')):
            with self.assertRaises(dict_lookup.LookupError) as caught:
                dict_lookup._fetch_json('https://example.invalid/x')
        self.assertEqual(str(caught.exception), 'offline')

    def test_supported_languages(self):
        self.assertTrue(dict_lookup.supported('Japanese'))
        self.assertTrue(dict_lookup.supported('english'))
        self.assertFalse(dict_lookup.supported('Hindi'))
        self.assertFalse(dict_lookup.supported(''))


class LayerIsolationTests(unittest.TestCase):
    def test_only_dict_lookup_touches_network(self):
        import ast
        for name in ['storage.py', 'quiz.py', 'settings.py', 'romaji.py', 'selection.py', 'speakplan.py', 'ai_check.py']:
            tree = ast.parse((BASE / 'addon/globalPlugins/vocabularySaver' / name).read_text(encoding='utf-8'))
            imports = [a.name for node in ast.walk(tree) if isinstance(node, ast.Import) for a in node.names]
            self.assertFalse(any('urllib' in i or 'dict_lookup' in i for i in imports), name)
            # ai_check (and the other pure modules) must never reach the
            # network or an AI API: no urllib or http imports anywhere.
            self.assertFalse(any('urllib' in i or i.startswith('http') for i in imports), name)


if __name__ == '__main__':
    unittest.main()
