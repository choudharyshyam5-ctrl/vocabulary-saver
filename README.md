# Vocabulary Saver

Vocabulary Saver is an NVDA add-on for language learners. You save words, their meanings and short notes, group them into lessons, read them back, and practise with a multiple-choice quiz. It was first made for studying Japanese, but it works with any language.

Your vocabulary is stored in a file on your own computer and is never sent anywhere. Only the optional word search connects to the internet: it sends the word you look up to free dictionary services to fetch meanings and example sentences.

## Features

- Save a word or grammar term with its meaning and optional notes.
- Group entries into lessons.
- Read a lesson's list in a read-only view, or edit it (change or delete entries).
- Save the text you have selected in any program as a new word.
- Organize lessons by language, and add your own languages.
- For Japanese lessons, romaji typed in the word field can be converted to hiragana, with an undo button.
- Each word can carry a reading (for example the hiragana reading of a kanji word). It is shown next to the word, with a romaji form, and spoken after it.
- In a lesson with a language set, words are spoken in that language through NVDA's automatic language switching.
- Look up a word online and save it with its meaning and an example sentence. The search detects whether you typed English or Japanese (kanji, kana or romaji) by itself.
- Check vocabulary with AI: export a ready-made text to paste into any AI chat, then paste the reply back to fill in Japanese readings and tidy meanings. The add-on itself never contacts an AI and needs no API key.
- After an install or update, a one-time what's-new notice sums up the changes and links to the feedback channel. It can be turned off in Settings.
- Multiple-choice quiz built from your saved words. The score is announced at the end and can be copied.
- Export your vocabulary to a JSON file and import it back, for backup or moving to another computer.
- Settings for the number of quiz questions, for announcing each question automatically, and for speaking readings.

## Requirements

- NVDA 2025.1 or later.
- Tested on NVDA 2026.2.

## Installation

1. Download the `.nvda-addon` file from the Releases page of this repository, or install it from the NVDA Add-on Store.
2. Press Enter on the downloaded file. NVDA asks you to confirm the installation.
3. Restart NVDA when asked.

## Usage

You can reach everything from the NVDA menu: press NVDA+N, open Tools, then Vocabulary Saver. The submenu contains:

- Add vocabulary
- Search word and add
- Read vocabulary list
- Edit vocabulary list
- Start MCQ quiz
- Lessons
- Check vocabulary with AI

### Adding a word

Open Add vocabulary, choose a lesson, then fill in the word or grammar term, the meaning, and optional notes. If you have no lessons yet, the lesson list shows "Create a new lesson".

To save a word you have selected in another program, select it and press NVDA+Alt+V.

### Searching for a word

Choose Search word and add, type a word, and press Search. The add-on detects the language on its own: kanji or kana are looked up as Japanese, and plain letters are looked up as English, except inside a Japanese lesson, where they are first tried as romaji against the Japanese dictionary and fall back to English. Japanese meanings come from Jisho and example sentences from Tatoeba; English meanings come from dictionaryapi.dev, with extra example sentences from Tatoeba. Choose a meaning and, if you like, an example sentence, then press Add to dictionary. The example is stored in the notes field with its source link, and a Japanese word's hiragana reading is saved with the entry. Searching needs an internet connection; only the word you type is sent to those services. If the word already exists, you can keep both entries, replace the old one, or cancel.

### Readings and Japanese speech

Some screen reader voices cannot read kanji, so every entry has an optional Reading field for the word's hiragana reading. The reading appears next to the word in the lists and details, together with a romaji form that any voice can read, and it is spoken after the word. Fill it in yourself when adding a word, let the online search fill it from the dictionary, or use Check vocabulary with AI to fill many at once.

When a lesson has a language set (Set language in Edit vocabulary list), the add-on speaks the word and its reading in that language using NVDA's automatic language switching, which is enabled by default. Meanings and notes stay in your usual voice, because they are written in your own language. To hear Japanese, your speech synthesizer needs a Japanese voice: NVDA's built-in eSpeak NG supports Japanese, and a dedicated Japanese voice such as a Windows OneCore voice sounds better. If the current synthesizer has no Japanese voice, NVDA tells you the language is not supported and speaks on in the default voice.

### Checking vocabulary with an AI

Choose Check vocabulary with AI from the Vocabulary Saver submenu, or the Check with AI button in Edit vocabulary list. Press Copy export text, paste it into any AI chat such as Gemini or ChatGPT, copy the reply, paste it into the reply box, and press Apply corrections. The AI is asked to fill in the hiragana reading of every Japanese word and to tidy the English of your meanings. Before anything is saved, the add-on tells you how many readings and meanings will change, and words, notes and lessons are never changed by this step. The add-on sends nothing by itself and needs no API key: you do the copying, so you see exactly what leaves your computer.

### Reading and editing a lesson

Choose Read vocabulary list or Edit vocabulary list, pick a lesson, and move through the words. The details box shows the full entry. Reading mode cannot change anything. Editing mode has buttons to add, edit and delete entries.

### Lessons, backup and restore

The Lessons dialog lets you create lessons and open any lesson for reading, editing or a quiz. You can group lessons by language: pick a language from the list at the top, or add your own with Add language. It also has Export JSON and Import JSON buttons. Importing asks for confirmation before it replaces your current data.

### Quiz

Choose Start MCQ quiz, pick a lesson, and answer each question by selecting one of the choices. The wrong choices are meanings taken from your other saved words, so a lesson needs a few entries first. When the quiz ends, your score is announced and you can copy it.

### Settings

Open NVDA menu > Preferences > Settings > Vocabulary Saver to set the number of quiz questions (10 by default, or all), whether each question is announced automatically, and whether the reading is spoken after the word in lessons with a set language, and whether the what's-new notice appears after an update.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| NVDA+Alt+V | Add vocabulary (uses the selected text, if any) |
| NVDA+Alt+B | Open the lessons dialog |
| NVDA+Alt+Q | Start a multiple-choice quiz |

You can change these in NVDA menu > Preferences > Input gestures, under the Vocabulary Saver category.

## Privacy

Your vocabulary stays in a local file on your computer. Apart from the optional word search described above, the add-on makes no network connections. The AI check only produces text for you to copy; your words reach an AI service only if you paste that text there yourself. The what's-new notice makes no network connection; its Telegram button only opens your web browser when you press it.

A note on upgrades: vocabulary saved by version 0.1.5 uses a newer file format that older versions of the add-on cannot open. If you need to go back to an older version, restore the backup file it keeps next to your vocabulary (the .previous.json or .v2-backup.json file).

## Testing

The author has tested the add-on with NVDA 2026.2, and it has also been used by other NVDA users, who reported that it works well. If you find a problem, please open an issue on GitHub and say which NVDA version you use.

## Changelog

### 0.1.5

- Every entry can store a reading (for example the hiragana reading of a kanji word), shown next to the word with a romaji form and spoken after it.
- In a lesson with a language set, words and readings are spoken in that language through NVDA's automatic language switching.
- Word search detects English and Japanese (kanji, kana or romaji) automatically; English searches also get Tatoeba example sentences.
- New Check vocabulary with AI: export your words for any AI chat to check, and apply its reply to fill readings and tidy meanings. No API key, no network call from the add-on.

### 0.1.4-dev

- Shortcuts changed to avoid clashes: NVDA+Alt+V adds a word, NVDA+Alt+B opens lessons, and the new NVDA+Alt+Q starts a quiz. NVDA+Shift+V is no longer used.

### 0.1.3-dev

- Online word search: look up a word and save it with its meaning and an example sentence. Japanese via Jisho and Tatoeba, English via dictionaryapi.dev.

### 0.1.2

- Lessons can be grouped by language, and you can add your own languages. For Japanese lessons, romaji can be converted to hiragana in the word field.

### 0.1.0

- First release: lessons, vocabulary entries, read and edit views, selected-text shortcut, JSON export and import, multiple-choice quiz, settings panel.

## Feedback

- Telegram channel: https://t.me/VocabularySaverNVDA
- Or open an issue on GitHub: https://github.com/choudharyshyam5-ctrl/vocabulary-saver/issues

## License

GNU General Public License, version 2. See the LICENSE file.

## Author

Shyam Choudhary. Source code and issues: https://github.com/choudharyshyam5-ctrl/vocabulary-saver
