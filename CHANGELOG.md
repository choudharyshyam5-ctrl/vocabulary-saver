# Changelog

## 0.1.5

- After an install or update, a one-time what's-new notice sums up the changes, with a button that opens the new Telegram feedback channel (https://t.me/VocabularySaverNVDA). It appears once per version, makes no network connection, and can be turned off in Settings.

- New Reading field on every entry: the hiragana reading of a Japanese word, shown next to the word in lists and details (with a romaji form for voices that cannot read Japanese) and spoken after the word. A new setting controls speaking the reading.
- Language-aware speech: in a lesson with a language set (Set language), the word and its reading are spoken in that language through NVDA's automatic language switching (enabled by default in NVDA). Meanings and notes stay in the default voice.
- Word search detects the language automatically: kanji and kana search Japanese; plain letters search English, except in a Japanese lesson where they are tried as romaji against the Japanese dictionary first, with an English fallback. No separate language step.
- English searches now also offer example sentences from Tatoeba (CC BY 2.0 FR), with the same author/license attribution as Japanese examples.
- New Tools > Vocabulary Saver > Check vocabulary with AI (also a button in Edit vocabulary list): copy a ready-made export text into any AI chat, paste the reply back, and apply the corrections. It fills Japanese hiragana readings and tidies English meanings. The add-on makes no AI or network call and needs no API key; a confirmation shows the exact counts before anything is saved, and words, notes and lessons are never changed.
- The online search now saves the dictionary's hiragana reading into the new Reading field automatically.
- Storage format is now version 3 (adds the reading field). Version 1 and 2 files are migrated automatically, and a rollback backup of the original file is kept next to the vocabulary file. Older add-on versions cannot read the new file.

## 0.1.4-dev

- Keyboard shortcuts changed to avoid clashes with other add-ons:
  - Add vocabulary moved from NVDA+Shift+V to NVDA+Alt+V (NVDA+Shift+V is also used by Vision Assistant Pro).
  - Open lessons moved from NVDA+Alt+V to NVDA+Alt+B.
  - New shortcut NVDA+Alt+Q starts a multiple-choice quiz directly.
- All three shortcuts can be remapped in Input Gestures under the Vocabulary Saver category.
- README, packaged help and changelog corrected: they now cover the language grouping, romaji conversion and word search added in 0.1.2 and 0.1.3-dev.

## 0.1.3-dev

- Tools > Vocabulary Saver > Search word and add: look up a word online and save it with its meaning and an example sentence. Japanese words use Jisho for meanings and Tatoeba for example sentences; English words use dictionaryapi.dev. No API key needed.
- The example sentence is stored in the notes field with its source link. Japanese examples have no embedded English translation because the translator credit could not be confirmed.
- If the word already exists, the add-on asks whether to keep both entries, replace the old one, or cancel.
- Lookups need an internet connection; only the word looked up is sent to those services.

## 0.1.2

- Lessons can be grouped by language, with an Add language button and a language filter in the Lessons dialog.
- For Japanese lessons, romaji typed in the word field can be converted to hiragana, with an Undo button.

## 0.1.1

- Documentation and manifest corrected for NVDA Add-on Store review. No code changes.

## 0.1.0

- First release.
- Lessons, with vocabulary and grammar entries (word, meaning, optional notes).
- Separate read-only and edit views for each lesson.
- Save selected text as a new word with NVDA+Alt+V (NVDA+Shift+V in 0.1.0 to 0.1.3-dev).
- Tools > Vocabulary Saver submenu in the NVDA menu.
- Multiple-choice quiz built from saved words, with the score announced at the end and a Copy score button.
- JSON export and import, with confirmation before import replaces existing data.
- Settings panel for the number of quiz questions and automatic question announcements.
- Data is stored locally. The add-on does not use the network.
- Tested by the author with NVDA 2026.2. Other users who installed it report that it works well.
