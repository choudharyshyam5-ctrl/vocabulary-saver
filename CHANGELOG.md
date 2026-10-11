# Changelog

## 0.1.0-dev - 11 October 2026

- First phase-1 source starter: lessons, manual word/meaning/notes, selected-text
  shortcut, editing/deleting entries, accessible native-control dialogs.
- Local schema-versioned Unicode JSON with atomic saves and recovery snapshots.
- Validated JSON export/import with explicit replace-all confirmation.
- Separate storage and selection tests, package builder, developer README.
- Added MCQ-only quiz in this SAME add-on: saved meanings as distractors, final
  score announced, explicit Copy score for user-controlled plain-text sharing.
- No AI, automatic external score sending, persistent quiz history or cloud sync.
- Not live-tested under Windows/NVDA. Not submitted to the Add-on Store.

- Added distinct Read vocabulary list and Edit vocabulary list paths per lesson;
  read mode has only browsing/details and Read selected entry, with no mutations.

- Add vocabulary is the first action; its lesson dropdown shows saved lessons
  or only Create a new lesson when empty, with atomic first lesson/entry save.

- Added Tools > Vocabulary Saver submenu with main actions and unload cleanup.

- Added minimal NVDA Settings panel: question count (10 default or All), and
  automatic question announcements (on by default). Quiz honors both.
