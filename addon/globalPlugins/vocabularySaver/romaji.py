"""Offline romaji/kana conversion and Japanese script detection.

Pure Python, no NVDA/wx dependency: unit-test directly. Converts lowercase
Hepburn romaji runs only. Existing kana/kanji, uppercase text and anything it
does not recognise pass through untouched, so mixed-script content is never
rewritten. Covers kana only - no kanji conversion.

Also provides the reverse direction (kana to romaji, for displaying a
reading to users whose speech cannot read Japanese) and small helpers to
detect Japanese script in typed text.
"""

# Longest keys are tried first (3 letters, then 2, then 1).
_TABLE = {
    'kya': 'きゃ', 'kyu': 'きゅ', 'kyo': 'きょ',
    'sha': 'しゃ', 'shu': 'しゅ', 'sho': 'しょ',
    'cha': 'ちゃ', 'chu': 'ちゅ', 'cho': 'ちょ',
    'nya': 'にゃ', 'nyu': 'にゅ', 'nyo': 'にょ',
    'hya': 'ひゃ', 'hyu': 'ひゅ', 'hyo': 'ひょ',
    'mya': 'みゃ', 'myu': 'みゅ', 'myo': 'みょ',
    'rya': 'りゃ', 'ryu': 'りゅ', 'ryo': 'りょ',
    'gya': 'ぎゃ', 'gyu': 'ぎゅ', 'gyo': 'ぎょ',
    'ja': 'じゃ', 'ju': 'じゅ', 'jo': 'じょ',
    'bya': 'びゃ', 'byu': 'びゅ', 'byo': 'びょ',
    'pya': 'ぴゃ', 'pyu': 'ぴゅ', 'pyo': 'ぴょ',
    'ka': 'か', 'ki': 'き', 'ku': 'く', 'ke': 'け', 'ko': 'こ',
    'sa': 'さ', 'shi': 'し', 'su': 'す', 'se': 'せ', 'so': 'そ',
    'ta': 'た', 'chi': 'ち', 'tsu': 'つ', 'te': 'て', 'to': 'と',
    'na': 'な', 'ni': 'に', 'nu': 'ぬ', 'ne': 'ね', 'no': 'の',
    'ha': 'は', 'hi': 'ひ', 'fu': 'ふ', 'he': 'へ', 'ho': 'ほ',
    'ma': 'ま', 'mi': 'み', 'mu': 'む', 'me': 'め', 'mo': 'も',
    'ya': 'や', 'yu': 'ゆ', 'yo': 'よ',
    'ra': 'ら', 'ri': 'り', 'ru': 'る', 're': 'れ', 'ro': 'ろ',
    'wa': 'わ', 'wo': 'を',
    'ga': 'が', 'gi': 'ぎ', 'gu': 'ぐ', 'ge': 'げ', 'go': 'ご',
    'za': 'ざ', 'ji': 'じ', 'zu': 'ず', 'ze': 'ぜ', 'zo': 'ぞ',
    'da': 'だ', 'di': 'ぢ', 'du': 'づ', 'de': 'で', 'do': 'ど',
    'ba': 'ば', 'bi': 'び', 'bu': 'ぶ', 'be': 'べ', 'bo': 'ぼ',
    'pa': 'ぱ', 'pi': 'ぴ', 'pu': 'ぷ', 'pe': 'ぺ', 'po': 'ぽ',
    'aa': 'ああ', 'ii': 'いい', 'uu': 'うう', 'ee': 'ええ', 'oo': 'おお', 'ou': 'おう',
    'a': 'あ', 'i': 'い', 'u': 'う', 'e': 'え', 'o': 'お',
}

_VOWELS = 'aiueo'


def _convert_run(run, word_final):
    """Convert one all-lowercase romaji run, or return None if it is not fully parseable.

    A run converts only as a whole: any letter that is not valid Hepburn romaji
    (l, v, x, q, ...) makes the entire run stay exactly as typed, so ordinary
    non-Japanese words are never half-converted. A trailing 'n' may stay
    pending while the user is still typing (word_final False).
    """
    output = []
    i, length = 0, len(run)
    while i < length:
        ch = run[i]
        nxt = run[i + 1] if i + 1 < length else ''
        # Syllabic n: doubled, before a consonant, or at the end of the run.
        if ch == 'n':
            if nxt == 'n':
                output.append('ん')
                i += 1
                continue
            if nxt and nxt not in _VOWELS + 'y':
                output.append('ん')
                i += 1
                continue
            if not nxt:
                if word_final:
                    output.append('ん')
                    i += 1
                    continue
                output.append('n')  # Still typing: keep the pending n.
                i += 1
                continue
            # n before a vowel or y: fall through to syllable matching (na, nya...).
        # Doubled consonant: small tsu, then the consonant starts the next syllable.
        if ch == nxt and ch not in _VOWELS:
            if i + 2 < length:  # Only when a syllable follows; trailing pairs stay pending.
                output.append('っ')
                i += 1
                continue
            return None
        for size in (3, 2, 1):
            chunk = run[i:i + size]
            if chunk in _TABLE:
                output.append(_TABLE[chunk])
                i += size
                break
        else:
            return None
    return ''.join(output)


def to_hiragana(text, final=True):
    """Convert lowercase romaji runs to hiragana; pass everything else through.

    Only fully lowercase ASCII letter runs are converted. Existing kana/kanji,
    mixed-case or uppercase words (Tokyo, JLPT), digits and punctuation pass
    through untouched, so mixed-script content is never rewritten.
    final=False leaves a trailing lone 'n' unconverted, for use while the user
    is still typing; final=True converts it to ん (word finished).
    """
    output = []
    i, length = 0, len(text)
    while i < length:
        ch = text[i]
        if ch.isascii() and ch.isalpha():
            end = i
            while end < length and text[end].isascii() and text[end].isalpha():
                end += 1
            run = text[i:end]
            if run.islower():
                # A run ending mid-text is followed by a break, so its trailing n is complete.
                converted = _convert_run(run, final or end < length)
                output.append(converted if converted is not None else run)
                # n' is the standard syllabic-n delimiter (kin'you): consume the
                # apostrophe so it never lands in the stored word.
                if converted is not None and run[-1] == 'n' and end < length and text[end] == "'":
                    end += 1
            else:
                output.append(run)
            i = end
        else:
            output.append(ch)
            i += 1
    return ''.join(output)


class ConversionSession:
    """Event adapter between the wx word field and to_hiragana. No wx dependency.

    Tracks the raw romaji the user actually typed so undo restores the exact
    original input, not an intermediate half-converted state. The raw buffer is
    trusted only while every user edit is a simple append at the end of the
    field; any deletion, mid-field edit or unclear change drops it to None, and
    undo then falls back to the exact field text from before the most recent
    automatic conversion (one step). No wx objects here: the dialog feeds
    observed field values in and applies returned values out.
    """

    def __init__(self, initial=''):
        self.field = initial
        # An empty field means everything typed afterwards is raw input; an
        # existing word cannot be reconstructed as raw romaji.
        self.raw = '' if not initial else None
        self.last_backup = None

    def user_edit(self, new_value, convert=True):
        """A user-caused text event (typing, paste, deletion) changed the field.

        convert=False keeps raw tracking without converting (conversion
        checkbox off or the lesson is not Japanese)."""
        if self.raw is not None and new_value.startswith(self.field):
            self.raw += new_value[len(self.field):]
        else:
            self.raw = None
        self.field = new_value
        if convert:
            converted = to_hiragana(new_value, final=False)
            if converted != new_value:
                self.last_backup = new_value
                self.field = converted
        return self.field

    def user_finalize(self):
        """Focus left the word field: finish pending syllables."""
        converted = to_hiragana(self.field, final=True)
        if converted != self.field:
            self.last_backup = self.field
            self.field = converted
        return self.field

    def undo(self):
        """Restore exact raw input when known, else one-step pre-conversion text.

        Returns (value, restored_raw). The dialog must disable conversion after
        an undo, otherwise the restored romaji would instantly reconvert.
        """
        if self.raw is not None and self.last_backup is not None:
            self.field, self.raw, self.last_backup = self.raw, None, None
            return self.field, True
        if self.last_backup is not None:
            self.field, self.last_backup = self.last_backup, None
            return self.field, False
        return self.field, False


# Kana -> romaji, the reverse of _TABLE. Values in _TABLE are unique, so this
# is a clean inversion; setdefault guards against any future duplicate.
_REVERSE = {}
for _romaji, _kana in _TABLE.items():
    _REVERSE.setdefault(_kana, _romaji)

_SMALL_Y = {'ゃ', 'ゅ', 'ょ'}


def has_japanese_script(text):
    """True when the text contains hiragana, katakana or kanji."""
    for char in text:
        code = ord(char)
        if (0x3040 <= code <= 0x30FF  # hiragana and katakana
                or 0xFF66 <= code <= 0xFF9D  # halfwidth katakana
                or 0x4E00 <= code <= 0x9FFF  # CJK unified ideographs
                or 0x3400 <= code <= 0x4DBF):  # CJK extension A
            return True
    return False


def has_kanji(text):
    for char in text:
        code = ord(char)
        if 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
            return True
    return False


def has_kana(text):
    for char in text:
        if 0x3040 <= ord(char) <= 0x30FF:
            return True
    return False


def has_ascii_letters(text):
    return any(char.isascii() and char.isalpha() for char in text)


def detect_lookup_language(text, lesson_language_name=''):
    """Pick the dictionary for a search word: script first, then the lesson.

    Japanese script (kanji, kana) always means a Japanese lookup, whichever
    lesson is selected. Plain Latin letters mean an English lookup, except in
    a Japanese lesson, where they are treated as romaji and tried against the
    Japanese dictionary first (the caller may fall back to English).
    """
    if has_japanese_script(text):
        return 'japanese'
    if lesson_language_name and lesson_language_name.casefold() == 'japanese':
        return 'japanese'
    return 'english'


def _to_hiragana_char(char):
    code = ord(char)
    if 0x30A1 <= code <= 0x30F6:  # katakana to hiragana
        return chr(code - 0x60)
    return char


def _cluster_romaji(text, index):
    """Romaji for the kana cluster at index (digraphs like きゃ included).

    Returns (romaji, next_index), or (None, index) when the character is not
    convertible kana.
    """
    first = _to_hiragana_char(text[index])
    if index + 1 < len(text):
        second = _to_hiragana_char(text[index + 1])
        if second in _SMALL_Y and first + second in _REVERSE:
            return _REVERSE[first + second], index + 2
    if first == 'ん':
        return 'n', index + 1
    if first in _REVERSE:
        return _REVERSE[first], index + 1
    return None, index


def to_romaji(text):
    """Convert kana runs to Hepburn romaji; pass everything else through.

    Kanji, Latin text, digits and punctuation are kept as they are, so a
    reading with mixed content still displays sensibly. The long-vowel mark
    becomes a hyphen. The conversion is approximate (n stays n before b/m/p),
    matching the forward table so to_hiragana(to_romaji(kana)) round-trips.
    """
    output = []
    i, length = 0, len(text)
    while i < length:
        char = text[i]
        if char == 'ー':
            output.append('-')
            i += 1
            continue
        hiragana = _to_hiragana_char(char)
        if hiragana == 'っ':  # Small tsu doubles the next consonant.
            romaji, _ = _cluster_romaji(text, i + 1)
            output.append(romaji[0] if romaji and romaji[0] not in _VOWELS else '')
            i += 1
            continue
        romaji, next_index = _cluster_romaji(text, i)
        if romaji is None:
            output.append(char)
            i += 1
            continue
        output.append(romaji)
        i = next_index
    return ''.join(output)
