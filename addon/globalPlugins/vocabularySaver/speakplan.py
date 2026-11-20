"""Build language-tagged speech plans. Pure Python: unit-test without NVDA.

A speech plan is a list of (text, language_code) segments. language_code None
means the user's default voice; a code like 'ja' asks NVDA to switch language
for that segment. The NVDA layer (nvda_speech.py) turns a plan into
LangChangeCommand speech; keeping the plan pure lets tests pin exactly what is
spoken and in which language.
"""

# NVDA/BCP 47 language codes for the starter languages and common additions.
# Custom languages simply get no code: their text is spoken in the default
# voice, never mis-tagged.
LANGUAGE_CODES = {
    'japanese': 'ja',
    'english': 'en',
    'korean': 'ko',
    'chinese': 'zh',
    'french': 'fr',
    'german': 'de',
    'spanish': 'es',
    'russian': 'ru',
    'italian': 'it',
    'hindi': 'hi',
}


def language_code(language_name):
    if not language_name:
        return None
    return LANGUAGE_CODES.get(language_name.casefold())


def word_segments(word, reading='', code=None, speak_reading=True):
    """The word (plus its reading when different), tagged with the language.

    The reading follows the word in brackets, so a word whose kanji the voice
    cannot read is still followed by its kana reading.
    """
    suffix = f' ({reading})' if speak_reading and reading and reading != word else ''
    return [(word + suffix, code)]


def entry_speech_segments(entry, code=None, speak_reading=True):
    """Spoken form of one entry: word and reading in the lesson language.

    Meaning and notes stay in the default voice: they are written in the
    learner's own language, and notes may mix several languages.
    """
    segments = [('Word: ', None)]
    segments.extend(word_segments(entry['word'], entry.get('reading', ''), code, speak_reading))
    segments.append(('. Meaning: ', None))
    segments.append((entry['meaning'], None))
    notes = entry.get('notes') or ''
    if notes:
        segments.append(('. Description / notes: ', None))
        segments.append((notes, None))
    segments.append(('.', None))
    return segments


def question_segments(index, total, word, reading='', code=None, speak_reading=True):
    """Spoken quiz question with the word (and reading) in the lesson language."""
    segments = [(f'Question {index + 1} of {total}. What is the meaning of ', None)]
    segments.extend(word_segments(word, reading, code, speak_reading))
    segments.append(('?', None))
    return segments


def plain_text(segments):
    """The same plan as one string, for the fallback path and for tests."""
    return ''.join(text for text, _ in segments)
