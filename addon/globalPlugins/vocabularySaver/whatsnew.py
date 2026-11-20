"""One-time "what's new" notice, shown once after an install or update.

Pure Python, no NVDA/wx dependency and no network: the notice only opens the
feedback channel in the browser when the user presses its button. The version
is read from the packaged manifest.ini so it can never drift from the release.
"""
import re
from pathlib import Path

FEEDBACK_URL = 'https://t.me/VocabularySaverNVDA'
FEEDBACK_LABEL = 'Give feedback on &Telegram'
FALLBACK_VERSION = '0.1.5'


def should_show(last_seen, current, enabled):
    """True when the notice should appear: the switch is on and the version is new.

    A fresh install has no stored version, so it counts as new and sees the
    notice once. The same version never shows it twice.
    """
    if not enabled or not current:
        return False
    return last_seen != current


def current_version():
    """The add-on version from the packaged manifest, with a fixed fallback."""
    try:
        manifest = Path(__file__).resolve().parents[2] / 'manifest.ini'
        match = re.search(
            r'^version\s*=\s*(\S+)\s*$',
            manifest.read_text(encoding='utf-8'),
            flags=re.MULTILINE,
        )
        if match:
            return match.group(1)
    except OSError:
        pass
    return FALLBACK_VERSION


def notice_text(version):
    """The dialog body: a short summary plus how feedback and privacy work."""
    return (
        f'Vocabulary Saver updated to {version}\n'
        '\n'
        'What is new:\n'
        '- Readings: every word can carry a reading, for example the hiragana '
        'reading of a kanji word, shown next to the word and spoken after it.\n'
        '- Language speech: set a lesson\'s language once, and words and readings '
        'are spoken in that language.\n'
        '- The word search detects English and Japanese by itself, including romaji.\n'
        '- Check vocabulary with AI: let any AI chat fill readings and tidy meanings. '
        'Nothing is sent until you paste it there yourself.\n'
        '- New shortcuts: NVDA+Alt+V adds a word, NVDA+Alt+B opens lessons, '
        'NVDA+Alt+Q starts a quiz.\n'
        '\n'
        'Feedback is welcome: press the Telegram button below, or use the GitHub '
        'Issues page. This notice appears once per version and makes no network '
        'connection; the button opens your browser only if you press it. You can '
        'turn this notice off in NVDA Settings, under Vocabulary Saver.'
    )
