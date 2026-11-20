# Testing

## Automated checks

From the project root:

```text
python -m unittest discover -s tests -v
python -m compileall -q addon tests build.py
```

Tests use temporary folders, not real NVDA data. Storage tests exercise CRUD,
Unicode, backup round trips, schema limits and migrations, invalid imports,
corrupted data, atomic-write failure, ID uniqueness, recovery snapshots and
AI-check patches. Speech-plan, reading-conversion, script-detection and
AI-reply tests pin the exact text and language tags. What's-new tests cover the
show/hide logic (fresh install, same version, upgrade, off-switch) and pin the
version, feedback link and privacy wording. Selection tests use fake
NVDA objects; they are not application interoperability tests.

## Manual checks

Before each release, load the add-on in NVDA and check these:

1. The add-on installs and loads, and the NVDA log shows no errors.
2. All three shortcuts appear in Input Gestures under Vocabulary Saver: NVDA+Alt+V (add), NVDA+Alt+B (lessons) and NVDA+Alt+Q (quiz).
3. Adding a word creates a lesson when none exists; cancelling creates nothing.
4. An empty word or meaning gives an error message and keeps the typed text.
5. Japanese text and multi-line notes are saved exactly and survive an NVDA restart.
6. Selected-text capture works in Notepad and in a browser, and manual entry still works when nothing is selected.
7. Every control in every dialog can be reached with Tab and has a spoken label.
8. Editing and deleting entries works, and focus stays in the dialog.
9. Export, then import: import asks for confirmation and keeps a copy of the previous data.
10. A bad JSON file is rejected without changing existing data.
11. The quiz runs, announces the score and can copy it.
12. The add-on can be disabled, removed and reloaded without errors.
13. A word saved with a reading shows the reading (and its romaji form) in the word lists and details, and Read selected entry speaks the word and then its reading.
14. In a lesson whose language is Japanese, Read selected entry and quiz questions speak the word in Japanese: with a Japanese-capable synthesizer voice you hear Japanese; with NVDA's built-in eSpeak NG you hear its Japanese voice; without either, NVDA says the language is not supported. NVDA's automatic language switching is enabled by default (NVDA menu > Preferences > Settings > Speech).
15. Search word and add: a kanji or kana word searches Japanese in any lesson; an English word searches English in an English lesson; romaji in a Japanese lesson searches Japanese first and falls back to English.
16. Check vocabulary with AI: Copy export text fills the clipboard, a pasted reply is validated, the confirmation lists the exact counts, and after applying, only readings and meanings have changed.
17. The what's-new notice appears once after install or upgrade with the right version, its Telegram button opens https://t.me/VocabularySaverNVDA in the browser, it stays away on the next start, and its switch in Settings turns it off.
18. Data saved by this version uses storage format 3. An older add-on version cannot read it: before downgrading, restore the .v2-backup.json (or .previous.json) file kept next to the vocabulary file.

## Test results

- Version 0.1.0 was tested by the author with NVDA 2026.2.
- Other NVDA users have installed and used it and report that it works well.
- The Python unit tests (storage, selection and quiz logic) pass.
