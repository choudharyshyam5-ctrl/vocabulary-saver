"""Speak a speech plan with NVDA's automatic language switching.

speech.speak accepts a sequence of text and SpeechCommand objects
(NVDA developer guide and speech/speech.py). LangChangeCommand('ja') switches
the synthesizer to Japanese for the following text; LangChangeCommand(None)
returns to the default voice. NVDA's "Automatic language switching" option is
enabled by default, so tagged text is spoken in Japanese whenever the active
synthesizer has a Japanese voice; otherwise NVDA says the switch is not
supported and speaks on in the default voice. Any failure falls back to plain
ui.message so an announcement is never lost.
"""
import speech
from speech.commands import LangChangeCommand
import ui
from logHandler import log


def speak_segments(segments):
    """Speak (text, language_code) segments from speakplan."""
    try:
        sequence = []
        for text, code in segments:
            if not text:
                continue
            if code:
                sequence.extend([LangChangeCommand(code), text, LangChangeCommand(None)])
            else:
                sequence.append(text)
        if sequence:
            speech.speak(sequence)
    except Exception:
        log.warning('Vocabulary Saver: language-tagged speech failed; using plain speech', exc_info=True)
        ui.message(''.join(text for text, _ in segments))
