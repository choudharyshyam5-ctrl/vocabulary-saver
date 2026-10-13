# Vocabulary Saver

Vocabulary Saver is an NVDA add-on for language learners. You save words, their meanings and short notes, group them into lessons, read them back, and practise with a multiple-choice quiz. It was first made for studying Japanese, but it works with any language.

All data is stored in a file on your own computer. The add-on does not connect to the internet and sends nothing anywhere.

## Features

- Save a word or grammar term with its meaning and optional notes.
- Group entries into lessons.
- Read a lesson's list in a read-only view, or edit it (change or delete entries).
- Save the text you have selected in any program as a new word.
- Multiple-choice quiz built from your saved words. The score is announced at the end and can be copied.
- Export your vocabulary to a JSON file and import it back, for backup or moving to another computer.
- Settings for the number of quiz questions and for announcing each question automatically.

## Requirements

- NVDA 2025.1 or later.
- Tested on NVDA 2026.2.

## Installation

1. Download the `.nvda-addon` file from the Releases page of this repository, or install it from the NVDA Add-on Store once it is listed.
2. Press Enter on the downloaded file. NVDA asks you to confirm the installation.
3. Restart NVDA when asked.

## Usage

You can reach everything from the NVDA menu: press NVDA+N, open Tools, then Vocabulary Saver. The submenu contains:

- Add vocabulary
- Read vocabulary list
- Edit vocabulary list
- Start MCQ quiz
- Lessons

### Adding a word

Open Add vocabulary, choose a lesson, then fill in the word or grammar term, the meaning, and optional notes. If you have no lessons yet, the lesson list shows "Create a new lesson".

To save a word you have selected in another program, select it and press NVDA+Shift+V.

### Reading and editing a lesson

Choose Read vocabulary list or Edit vocabulary list, pick a lesson, and move through the words. The details box shows the full entry. Reading mode cannot change anything. Editing mode has buttons to add, edit and delete entries.

### Lessons, backup and restore

The Lessons dialog lets you create lessons and open any lesson for reading, editing or a quiz. It also has Export JSON and Import JSON buttons. Importing asks for confirmation before it replaces your current data.

### Quiz

Choose Start MCQ quiz, pick a lesson, and answer each question by selecting one of the choices. The wrong choices are meanings taken from your other saved words, so a lesson needs a few entries first. When the quiz ends, your score is announced and you can copy it.

### Settings

Open NVDA menu > Preferences > Settings > Vocabulary Saver to set the number of quiz questions (10 by default, or all) and whether each question is announced automatically.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| NVDA+Shift+V | Add vocabulary (uses the selected text, if any) |
| NVDA+Alt+V | Open the lessons dialog |

You can change these in NVDA menu > Preferences > Input gestures, under the Vocabulary Saver category.

## Privacy

Your vocabulary stays in a local file on your computer. The add-on makes no network connections.

## Testing

The author has tested the add-on with NVDA 2026.2, and it has also been used by other NVDA users, who reported that it works well. If you find a problem, please open an issue on GitHub and say which NVDA version you use.

## Changelog

### 0.1.0

- First release: lessons, vocabulary entries, read and edit views, selected-text shortcut, JSON export and import, multiple-choice quiz, settings panel.

## License

GNU General Public License, version 2. See the LICENSE file.

## Author

Shyam Choudhary. Source code and issues: https://github.com/choudharyshyam5-ctrl/vocabulary-saver
