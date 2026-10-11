# Vocabulary Saver: NVDA add-on starter

Prepared for Shyam Choudhary, 11 October 2026. Development version 0.1.0-dev.

Learn Japanese vocabulary the easy way! Save words, meanings and grammar notes lesson by lesson, and test yourself with fun quizzes. Made for Japanese learners.

## Status: source starter, not a tested release

This is phase 1 of ONE add-on for Japanese learners: Japanese vocabulary and
grammar entries grouped into lessons,
with local storage, JSON backup and a simple MCQ practice quiz. The code is written for NVDA 2025.1+ APIs
and Python 3.11-compatible syntax. Current NVDA is newer than 2025.x and has
moved to Python 3.13; confirm your version in NVDA Help > About.

Python compilation and automated storage tests are not live NVDA testing.
No Windows NVDA or wxPython runtime was available during preparation. Keyboard
navigation, screen-reader announcements, dialog layout, selected-text capture,
and installation still need the manual checks below. Do not publish this as a
stable release until those checks pass on your actual NVDA version.

The source manifest's `lastTestedNVDAVersion = 2025.1` is an explicitly marked
DEVELOPMENT PLACEHOLDER, not a statement that NVDA 2025.1 was tested. The build
script requires you to enter a version you have actually tested. For your first
runtime check, load the plugin through NVDA's development scratchpad instead
of packaging an untested compatibility assurance.

## Features and keys

- NVDA+Shift+V: open Add vocabulary with selected text prefilled when available.
- NVDA+Alt+V: open the lesson window, with Add vocabulary first, plus a lesson
  selector and distinct Read vocabulary list / Edit vocabulary list buttons.
- The first action is Add vocabulary. It opens a labelled Lesson dropdown.
  Existing lessons appear for selection. If none exist, its only option is
  Create a new lesson, with a Lesson name field below it. Enter word/grammar
  term, meaning and optional notes, then save. The first lesson and entry save
  together; Cancel or invalid input creates neither.
- Read vocabulary list opens a read-only lesson snapshot: arrow through Words,
  Tab to Details, or press Read selected entry to hear word, meaning and notes.
  There are no add/edit/delete controls in this mode.
- Edit vocabulary list opens the existing manager with add/edit/delete, lesson
  creation, JSON backups and quiz. With no lessons, use Edit then New lesson.
- Browse the lesson choice and word list with arrows. Each word list item includes
  its meaning; full notes remain available in the read-only details control.
- New lesson, Add entry, Edit entry, Delete entry, Export JSON, Import JSON, Start quiz.
- Tab / Shift+Tab move between controls. Native buttons work with Space.
  Alt+the underlined letter activates labels/buttons. Escape closes dialogs;
  Cancel in Add/Edit discards unsaved text.
- Word and meaning are required; notes are optional. Unicode/Japanese works.
- Selected text comes from the focused application's TextInfo or its browse-mode
  interceptor, not the clipboard. If selection is unsupported, empty, or longer
  than 200 characters, type the word manually. Clipboard contents are untouched.
- The user reviews the selected word and fills the meaning before saving.
- No automatic dictionary, AI, network request, cloud sync or automatic score sending.

NVDA is the modifier key configured in your NVDA keyboard settings (usually
Insert and/or Caps Lock). Another add-on may already use these keys; change them
through Input Gestures if necessary.

## NVDA Tools menu

Open NVDA menu > Tools > Vocabulary Saver. Its submenu provides Add vocabulary,
Read vocabulary list, Edit vocabulary list, Start MCQ quiz, and Lessons.
Read/Edit/Quiz menu actions ask you to choose a saved lesson before opening that
path. Add uses the same lesson dropdown as the hotkey. Lessons opens the main
lesson chooser. Menu items are removed when the plugin unloads, and are not
installed in secure mode. Keyboard shortcuts remain available as before.

## Change keyboard gestures

After the plugin is loaded, open NVDA menu > Preferences > Input Gestures.
Find the category "Vocabulary Saver". Select "Add a vocabulary entry, using
selected text when available" or "Browse vocabulary lessons and manage entries
or backups". Use Add, press your desired key combination, and confirm it.
Remove an unwanted binding with Remove. Save the dialog with OK.
Use NVDA+1 for Input Help to check what a gesture does without running it.

## Exact source tree

```text
VocabularySaver/
  README.md
  CHANGELOG.md
  TESTING.md
  build.py
  addon/
    manifest.ini
    doc/
      en/
        readme.html
    globalPlugins/
      vocabularySaver/
        __init__.py
        selection.py
        storage.py
        dialogs.py
        lessonDialogs.py
        quiz.py
        quizDialogs.py
        settings.py
  tests/
    test_storage.py
    test_selection.py
    test_quiz.py
```

`__init__.py` is the GlobalPlugin entry point: gestures, selected-word capture,
dialog lifecycle, and the NVDA configuration path. `selection.py` reads selected
text. `storage.py` is independent of NVDA and wx: schema checks, Unicode JSON,
atomic writes and CRUD. `lessonDialogs.py` separates the lesson chooser/read-only reader from editing.
`dialogs.py` holds the editing manager and entry controls. `quiz.py` generates and scores
MCQs; `quizDialogs.py` presents questions and the copyable result.
`build.py` creates the install archive, excluding Python caches. Tests can run
on ordinary Python without NVDA installed. NVDA supplies wxPython itself; do
not install a separate wxPython into NVDA.

The actual NVDA gesture map name is `__gestures`, without trailing underscores.
The script decorators provide descriptions and the category for Input Gestures.

## First runtime test: development scratchpad

Use a spare NVDA configuration or portable copy for development and export any
existing vocabulary before modifying code. Do not run two NVDA processes against
the same vocabulary configuration directory.

1. Open NVDA menu > Preferences > Settings > Advanced.
2. Read/accept the advanced-settings caution. Enable "Enable loading custom code
   from Developer Scratchpad directory". This is for development, not normal
   installation.
3. Use "Open developer scratchpad directory". Inside it, create `globalPlugins`
   if missing.
4. Copy the WHOLE `addon/globalPlugins/vocabularySaver` folder into that folder.
   Result: `scratchpad/globalPlugins/vocabularySaver/__init__.py`.
5. Restart NVDA. Check the manual checklist in TESTING.md. If it fails, look in
   NVDA Tools > View log; copy errors, not your private vocabulary, for debugging.
6. Record the actual working NVDA version. Remove the scratchpad copy and
   disable scratchpad loading before installing a packaged copy. Loading both
   copies can conflict.

No manifest is loaded by this scratchpad method. Do not copy the outer
VocabularySaver source folder to globalPlugins.

## Build a .nvda-addon file

From the extracted VocabularySaver folder, in a Windows terminal with Python:

```bat
py -3.11 -m unittest discover -s tests -v
py -3.11 -m compileall -q addon tests build.py
py -3.11 build.py --tested-nvda-version YOUR_TESTED_VERSION
```

Replace YOUR_TESTED_VERSION with a numeric version you actually checked, such
as the value shown in Help > About. You can use Python 3.13 instead if that is
what is installed; the build script does not depend on NVDA. A successful build
prints `dist/vocabularySaver-0.1.0-dev.nvda-addon`.

A .nvda-addon file is a ZIP archive with `manifest.ini`, `globalPlugins/` and
`doc/` directly at its root. It must NOT have an outer `addon/` or
`VocabularySaver/` folder. The SOURCE ZIP delivered with this README is not an
install package. Renaming that source ZIP to .nvda-addon will not work.

The builder rewrites lastTestedNVDAVersion inside the package to the tested
version you supply. It does not alter the source manifest or run NVDA for you.
Before a public release, also set an honest tested version in the source
manifest, choose a release version, and update the filename in build.py.

## Install a built package

1. Close/remove the scratchpad copy first.
2. Open the trusted .nvda-addon file in File Explorer, or in NVDA's Add-on Store
   use "Install from external source" and select that package.
3. Read the installation/compatibility warnings, confirm installation, then
   restart NVDA when requested.
4. Try NVDA+Alt+V and create a test lesson. Check every item in TESTING.md again.

This add-on is not currently listed in the Add-on Store. After future accepted
submission, users can search for Vocabulary Saver in NVDA menu > Tools >
Add-on Store > Available add-ons, select it, install, and restart NVDA.
Do not override a compatibility warning just because a package compiles.

## Local data, backup and recovery

Data lives at:

```text
<NVDA user configuration directory>/vocabularySaver/vocabulary.json
```

The code derives that directory from NVDA's `globalVars.appArgs.configPath`;
it does not hard-code AppData. Installed and portable NVDA can therefore use
different locations. Use NVDA's user-configuration-folder shortcut when
available, or inspect your portable/configuration directory. Do not save data
inside the add-on directory, which can be replaced during updates.

- Every successful change is persisted immediately. There is no separate Save
  button in the manager.
- Writes use a temporary sibling file and atomic replacement. A disk/permission
  error is shown, and failed changes do not update the in-memory store.
- `vocabulary.previous.json` keeps the state before the last saved change.
- Export JSON lets you choose a separate backup location. Copy that file to
  another device or storage service yourself. Local snapshots are not a backup
  against disk failure.
- Import JSON validates the ENTIRE file before saving. Import REPLACES all
  lessons/entries; it does not merge. A confirmation is required.
- `vocabulary.before-import.json` keeps the state immediately before the latest
  successful import attempt's commit. A later import overwrites this snapshot.
- Invalid/corrupt storage is never silently reset. The plugin refuses to open
  it and leaves it untouched.

For recovery: close the manager and exit NVDA, make a copy of ALL vocabulary
files, and replace `vocabulary.json` with a known-good exported JSON or recovery
snapshot. Restart NVDA. If the snapshot is invalid too, keep the copies for
repair, rather than deleting your only record. Removing the add-on does not
intentionally delete this separate data directory; removing the whole NVDA
configuration can delete it.

Data is plain UTF-8 JSON, not encrypted. Anyone with access to your Windows
account, backups, or the file can read it. Nothing is sent to the internet by
this starter. Limits: 5 MiB per file, 500 lessons, 20,000 entries, 100-character
lesson names, 200-character words, 2,000-character meanings, 10,000-character
notes. Lesson names must be unique ignoring case; duplicate words are allowed
for different meanings. There is no lesson rename/delete or search yet.

Example schema:

```json
{
  "schemaVersion": 1,
  "lessons": [
    {
      "id": "unique-lesson-id",
      "name": "Lesson 1",
      "entries": [
        {
          "id": "unique-entry-id",
          "word": "neko",
          "meaning": "cat",
          "notes": "Japanese noun"
        }
      ]
    }
  ]
}
```

The importer rejects duplicate IDs, duplicate JSON keys, unsupported schema
versions, unexpected fields, and wrong types. A future schema must have a
migration path; do not simply add fields to existing version-1 backups.

## MCQ quiz included in version 0.1

Choose a lesson, open Edit vocabulary list, then activate Start quiz (Alt+Q). This local
practice quiz asks "What is the meaning of [word]?" and uses saved meanings
from that same lesson as distractors. No invented definitions or AI are used.

- At least two distinct meanings are required. Two or three meanings produce
  two or three options; four or more produce four options per question.
- Up to the configured number of unambiguous words are asked once, in random
  order, with shuffled options (default 10; choose All to ask every usable word).
  Duplicate identical words are deduplicated. Words with multiple distinct
  meanings in the lesson are skipped to avoid ambiguous word-only questions.
- Use arrows in the labelled Answer choice, then Submit answer. No option is
  preselected. The next question is announced if automatic announcements are on;
  the Question text remains readable either way.
- Finish quiz announces the final score and opens a read-only result dialog.
  Copy score copies plain text to the clipboard only after you press it.
  Paste into WhatsApp, email or another app yourself to share. Nothing is sent
  automatically. The result includes only lesson name, score and quiz mode,
  not the vocabulary entries or notes.
- Cancel exits without a result. Answers cannot be changed after submission.
  No per-question feedback, explanations, history, persistent scores, timer,
  or reverse-meaning mode yet. Export/import applies to vocabulary,
  not quiz results. Save copied results yourself if needed.

`quiz.py` is pure Python and works on a snapshot from `Store.lessons`; it cannot
change saved vocabulary. `quizDialogs.py` is separate wx presentation. This is
ONE add-on, not a separate test add-on. The generator checks text equality, not
semantic similarity: meanings that are synonyms may make poor distractors.
Choose precise definitions in your lesson and treat this as practice, not a
certified assessment. Score labels and question quality can be improved later.

## Settings (exactly two options)

Open NVDA menu > Preferences > Settings > Vocabulary Saver.

1. Number of questions per MCQ quiz: default 10. Type any whole number from 1
   to 20000 into the labelled combo box, or choose All from its dropdown.
   All asks every usable word in the chosen lesson; a numeric limit asks fewer
   if the lesson has fewer usable words. Questions are randomly sampled after
   ambiguous/duplicate words are removed.
2. Announce each question automatically when it appears: default on. Turn off
   to read the labelled Question text yourself. Answer choices and the final
   score remain accessible; the final score is still announced.

Settings save through NVDA's normal settings/profile mechanism. Cancel does not
apply changes. No extra options, account controls or network settings are added.

## Later improvements

Optional Gemini correction remains out of scope. Keep API handling in a new
module separate from storage/UI, require review before sending or changing
entries, and keep secrets out of vocabulary JSON.

Improve this same add-on's MCQ module later. Any persistent quiz history should
use a separate versioned file so vocabulary schema 1 stays compatible. External
score sharing should remain an explicit reviewed action. No cloud/Firebase code
is included now.

## GitHub hosting and NVDA Add-on Store submission

Nothing has been uploaded or submitted on your behalf.

1. Create a GitHub repository for the SOURCE, for example VocabularySaver.
   Add source, README, tests and changelog. Keep private vocabulary data, exports,
   credentials, Python caches and temporary files out of Git.
2. Choose a license before inviting others to reuse the code. No publication
   license has been selected for you in this starter.
3. Test with NVDA, finish metadata (including a real repository URL in the
   manifest's `url` field), then build a versioned .nvda-addon.
4. Create a GitHub Release for that version and attach the .nvda-addon as a
   release asset. Users need the asset, not GitHub's auto-generated source ZIP.
5. For the Store, follow the official nvaccess/addon-datastore submission guide
   linked below. Open its "Add-on registration" issue form. Provide the release
   download URL and metadata matching the manifest. The process generates a
   metadata pull request and runs validation/security checks.
6. First-time publishers need approval for their add-on. The official guide
   says this can take up to two weeks. Address any failed checks as directed;
   Store availability is not immediate or guaranteed.

A valid downloadable package, matching manifest/metadata, appropriate NVDA API
versions, repository/homepage URL, and the download's SHA-256 are part of the
submission validation. Store listing does not mean a human audited the code.
For a Store-ready project, consider moving this source into the official NVDA
add-on template and adding translation support, CI and an agreed license.

## Verified reference links

- NVDA developer guide (global plugins, script properties, manifest, scratchpad):
  https://download.nvaccess.org/documentation/developerGuide.html
- NVDA user guide (Add-on Store, Input Gestures, Advanced settings):
  https://download.nvaccess.org/documentation/userGuide.html
- 2025.1 gesture implementation (__gestures):
  https://github.com/nvaccess/nvda/blob/release-2025.1/source/baseObject.py
- 2025.1 selection reporting implementation:
  https://github.com/nvaccess/nvda/blob/release-2025.1/source/globalCommands.py
- NVDA Python 3.13 transition:
  https://github.com/nvaccess/nvda/issues/18591
- Add-on Store repository:
  https://github.com/nvaccess/addon-datastore
- Official Store submission guide:
  https://github.com/nvaccess/addon-datastore/blob/master/docs/submitters/submissionGuide.md

These links describe the checked workflow, not proof that this starter has
passed live NVDA testing.
