"""Export vocabulary for an outside AI check, and parse the AI's reply.

Pure Python, no NVDA/wx dependency and no network: the user copies the export
text into any AI chat and pastes the reply back themselves. The add-on never
calls an AI. Field limits mirror storage.py so parsed replies can be applied
straight to the store (keep them in sync).
"""
import json

MARKER = 'vocabularySaverAiCheck'
FORMAT_VERSION = 1
MAX_REPLY_BYTES = 5 * 1024 * 1024
# Same limits as storage.py fields.
WORD_LIMIT = 200
MEANING_LIMIT = 2000
READING_LIMIT = 200

PROMPT = """Vocabulary Saver: AI vocabulary check

You are checking a language learner's saved vocabulary. The JSON block at the
end lists lessons with entries. Each entry has entryId, word, reading and
meaning.

Do exactly this:
1. For every Japanese word written with kanji, fill "reading" with its
   standard reading in hiragana only (never katakana, never romaji).
2. For a Japanese word already written in kana, copy the word into "reading"
   converted to hiragana.
3. For words in other languages, leave "reading" empty.
4. Tidy the English in "meaning": fix spelling and grammar, keep it short,
   and keep every saved sense. Do not translate meanings into another
   language.
5. Never change "word", never add or remove entries or lessons, and keep
   every entryId unchanged.

Reply with ONLY the corrected JSON block, in exactly the same structure as
below, starting with {""" + '"vocabularySaverAiCheck": 1' + """}. No explanation before or after it.

JSON to correct:
"""


class AICheckError(ValueError):
    """The reply text cannot be used."""


def build_ai_export(data):
    """The prompt plus a compact JSON list of every lesson and entry."""
    languages = {x['id']: x['name'] for x in data['languages']}
    lessons = []
    for lesson in data['lessons']:
        lessons.append({
            'lessonId': lesson['id'],
            'lesson': lesson['name'],
            'language': languages.get(lesson['languageId'], ''),
            'entries': [
                {'entryId': entry['id'], 'word': entry['word'],
                 'reading': entry['reading'], 'meaning': entry['meaning']}
                for entry in lesson['entries']
            ],
        })
    payload = {MARKER: FORMAT_VERSION, 'lessons': lessons}
    return PROMPT + json.dumps(payload, ensure_ascii=False, indent=2) + '\n'


def _extract_json(reply):
    """Find the marked JSON object inside arbitrary reply text.

    The marker phrase can appear more than once (for example when the whole
    export text is pasted back), so occurrences are tried from the last one:
    the real block is the one that parses into the marked object.
    """
    marker = f'"{MARKER}"'
    occurrences = [i for i in range(len(reply)) if reply.startswith(marker, i)]
    if not occurrences:
        raise AICheckError(
            'The reply does not contain the Vocabulary Saver JSON block. '
            'Copy the AI reply that starts with the JSON block and paste it again.'
        )
    for marker_index in reversed(occurrences):
        start = reply.rfind('{', 0, marker_index)
        if start == -1:
            continue
        try:
            payload, _ = json.JSONDecoder().raw_decode(reply[start:])
        except ValueError:
            continue
        if isinstance(payload, dict) and payload.get(MARKER) == FORMAT_VERSION and isinstance(payload.get('lessons'), list):
            return payload
    raise AICheckError('The JSON block in the reply is incomplete or damaged. Copy the whole block and paste it again.')


def _clean(value, label, limit, required=False):
    if not isinstance(value, str):
        raise AICheckError(f'{label} must be text.')
    value = value.strip()
    if required and not value:
        raise AICheckError(f'{label} is empty.')
    if len(value) > limit or '\x00' in value:
        raise AICheckError(f'{label} is too long or contains a forbidden character.')
    return value


def parse_ai_reply(reply, data):
    """Validate the reply against current data; return patches and counts.

    Only entries whose lessonId and entryId both exist are updated, and only
    their reading and meaning. Word changes the AI may have made are ignored
    on purpose: the stored word is never overwritten from a reply.

    Returns {'patches': [...], 'readings': n, 'meanings': n, 'skipped': n}.
    Raises AICheckError when nothing usable can be found at all.
    """
    if len(reply.encode('utf-8')) > MAX_REPLY_BYTES:
        raise AICheckError('The pasted reply is too large to be a vocabulary check.')
    payload = _extract_json(reply)
    lessons = payload['lessons']
    known_lessons = {lesson['id']: lesson for lesson in data['lessons']}
    known_entries = {
        entry['id']: (lesson, entry)
        for lesson in data['lessons'] for entry in lesson['entries']
    }
    patches, readings, meanings, skipped = [], 0, 0, 0
    for lesson in lessons:
        if not isinstance(lesson, dict) or lesson.get('lessonId') not in known_lessons:
            skipped += 1
            continue
        entries = lesson.get('entries')
        if not isinstance(entries, list):
            skipped += 1
            continue
        for item in entries:
            if not isinstance(item, dict) or item.get('entryId') not in known_entries:
                skipped += 1
                continue
            current_lesson, current = known_entries[item['entryId']]
            if current_lesson['id'] != lesson['lessonId']:
                skipped += 1  # A real entry, but quoted under the wrong lesson.
                continue
            patch = {'lessonId': lesson['lessonId'], 'entryId': item['entryId']}
            if 'reading' in item:
                reading = _clean(item['reading'], 'A reading', READING_LIMIT)
                if reading != current['reading']:
                    patch['reading'] = reading
                    readings += 1
            if 'meaning' in item:
                meaning = _clean(item['meaning'], 'A meaning', MEANING_LIMIT, required=True)
                if meaning != current['meaning']:
                    patch['meaning'] = meaning
                    meanings += 1
            if len(patch) > 2:
                patches.append(patch)
    return {'patches': patches, 'readings': readings, 'meanings': meanings, 'skipped': skipped}
