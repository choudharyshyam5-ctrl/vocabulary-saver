"""Online dictionary lookup for the word search feature.

Network access lives only in _fetch_json; every parse function is pure so the
test suite runs offline against recorded responses. Sources:
- Japanese words: Jisho (unofficial free API over JMdict data), no key.
- Example sentences: Tatoeba (CC BY 2.0 FR corpus), no key - Japanese
  sentences for Japanese words, English sentences for English words.
- English words and inline examples: dictionaryapi.dev (Free Dictionary API),
  no key.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT_SECONDS = 10
USER_AGENT = 'VocabularySaver-NVDA-addon'


class LookupError(Exception):
    """kind: 'offline' | 'not_found' | 'bad_response'."""


def _fetch_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as error:
        raise LookupError('not_found' if error.code == 404 else 'offline') from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise LookupError('offline') from error
    except (UnicodeError, ValueError) as error:
        raise LookupError('bad_response') from error


def jisho_url(word):
    return 'https://jisho.org/api/v1/search/words?keyword=' + urllib.parse.quote(word)


def tatoeba_url(word, from_lang='jpn', to_lang='eng'):
    return ('https://tatoeba.org/en/api_v0/search?from=' + from_lang + '&to=' + to_lang
            + '&query=' + urllib.parse.quote(word))


def english_url(word):
    return 'https://api.dictionaryapi.dev/api/v2/entries/en/' + urllib.parse.quote(word.strip().lower())


def parse_jisho(payload):
    """Jisho entries -> word, reading, meanings, jlpt. No example sentences here."""
    results = []
    for entry in (payload or {}).get('data') or []:
        forms = entry.get('japanese') or []
        first = forms[0] if forms else {}
        word = first.get('word') or first.get('reading')
        if not word:
            continue
        reading = first.get('reading') or ''
        meanings = []
        for sense in entry.get('senses') or []:
            text = '; '.join(sense.get('english_definitions') or [])
            if text and text not in meanings:
                meanings.append(text)
        jlpt = entry.get('jlpt') or []
        level = jlpt[0].replace('jlpt-', '').upper() if jlpt else ''
        results.append({'word': word, 'reading': reading, 'meanings': meanings, 'jlpt': level})
    return results


def parse_tatoeba(payload, from_lang='jpn', to_lang='eng', limit=5):
    """Tatoeba sentences in from_lang with a to_lang translation and license.

    The sentence is returned as 'text'; its translation is kept only as a
    linked sentence ID, never embedded (the API gives no translation author).
    A kana transcription is included for Japanese sentences.
    """
    examples = []
    for sentence in (payload or {}).get('results') or []:
        if sentence.get('lang') != from_lang:
            continue
        text = sentence.get('text') or ''
        if not text:
            continue
        translation_id = None
        for group in sentence.get('translations') or []:
            for item in group:
                if item.get('lang') == to_lang and item.get('text'):
                    translation_id = item.get('id')
                    break
            if translation_id:
                break
        reading = ''
        if from_lang == 'jpn':
            for item in sentence.get('transcriptions') or []:
                if item.get('script') == 'Hrkt' and item.get('text'):
                    reading = item['text']
                    break
        user = sentence.get('user') or {}
        examples.append({'text': text, 'lang': from_lang, 'reading': reading,
                         'id': sentence.get('id'), 'author': user.get('username') or '',
                         'license': sentence.get('license') or '',
                         'translation_id': translation_id})
        if len(examples) >= limit:
            break
    return examples


def parse_english(payload):
    """dictionaryapi.dev entries -> word, meanings, examples (inline per definition)."""
    results = []
    for entry in payload or []:
        word = entry.get('word') or ''
        meanings, examples = [], []
        for block in entry.get('meanings') or []:
            part = block.get('partOfSpeech') or ''
            for definition in block.get('definitions') or []:
                text = definition.get('definition') or ''
                if text:
                    meanings.append(f'({part}) {text}' if part else text)
                example = definition.get('example')
                if example:
                    examples.append(example)
        if word and meanings:
            results.append({'word': word, 'meanings': meanings[:6], 'examples': examples[:5],
                            'license': entry.get('license') or {},
                            'sourceUrls': entry.get('sourceUrls') or []})
    return results


def lookup_japanese(word, fetcher=_fetch_json):
    entries = parse_jisho(fetcher(jisho_url(word)))
    if not entries:
        raise LookupError('not_found')
    return {'source': 'Jisho (JMdict)', 'entries': entries}


def lookup_japanese_examples(word, limit=5, fetcher=_fetch_json):
    return {'source': 'Tatoeba (CC BY 2.0 FR)', 'examples': parse_tatoeba(fetcher(tatoeba_url(word)), 'jpn', 'eng', limit)}


def lookup_english_examples(word, limit=5, fetcher=_fetch_json):
    """English example sentences from Tatoeba, licensed CC BY 2.0 FR."""
    return {'source': 'Tatoeba (CC BY 2.0 FR)',
            'examples': parse_tatoeba(fetcher(tatoeba_url(word, 'eng', 'jpn')), 'eng', 'jpn', limit)}


def lookup_english(word, fetcher=_fetch_json):
    entries = parse_english(fetcher(english_url(word)))
    if not entries:
        raise LookupError('not_found')
    return {'source': 'dictionaryapi.dev', 'entries': entries}


def supported(language_name):
    return language_name.casefold() in ('japanese', 'english')


def tatoeba_example_text(example):
    """Display/save form of a Tatoeba example: the sentence itself only.

    The translation is deliberately not embedded: the API provides no author
    or license for translations, so only a link to the original is kept (see
    tatoeba_attribution).
    """
    return example['text']


def tatoeba_attribution(example):
    """Credit lines kept with the example wherever it is saved/exported.

    The sentence gets its author, license and link (CC BY 2.0 FR obligations).
    The translation is a separate Tatoeba sentence whose author the search API
    does not return, so it is credited by its own sentence ID and link
    instead - never to the sentence's author.
    """
    sentence_id = example.get('id')
    author = example.get('author') or 'a Tatoeba member'
    license_name = example.get('license') or 'CC BY 2.0 FR'
    link = f'https://tatoeba.org/en/sentences/show/{sentence_id}' if sentence_id else 'https://tatoeba.org'
    line = f'Example from Tatoeba sentence #{sentence_id} by {author}, {license_name} ({link})'
    translation_id = example.get('translation_id')
    if translation_id:
        line += (f' Translation not embedded (its author is not provided by the API); '
                 f'see https://tatoeba.org/en/sentences/show/{translation_id}')
    return line


def english_attribution(entry):
    """Credit line for dictionaryapi.dev meanings/examples, from the entry's own license and sourceUrls."""
    license_info = entry.get('license') or {}
    name = license_info.get('name') or ''
    url = license_info.get('url') or ''
    sources = entry.get('sourceUrls') or []
    parts = ['Meanings and examples via dictionaryapi.dev']
    if name:
        parts.append(f'license {name}' + (f' ({url})' if url else ''))
    if sources:
        parts.append(f'source: {sources[0]}')
    return ', '.join(parts) + '.'


JISHI_ATTRIBUTION = ('Meanings via Jisho (https://jisho.org), JMdict data '
                     '(CC BY-SA 4.0, https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project).')
