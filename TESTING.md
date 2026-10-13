# Testing

## Automated checks

From the project root:

```text
python -m unittest discover -s tests -v
python -m compileall -q addon tests build.py
```

Tests use temporary folders, not real NVDA data. Storage tests exercise CRUD,
Unicode, backup round trips, schema limits, invalid imports, corrupted data,
atomic-write failure, ID uniqueness and recovery snapshots. Selection tests
use fake NVDA objects; they are not application interoperability tests.

## Manual checks

Before each release, load the add-on in NVDA and check these:

1. The add-on installs and loads, and the NVDA log shows no errors.
2. Both shortcuts appear in Input Gestures under Vocabulary Saver.
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

## Test results

- Version 0.1.0 was tested by the author with NVDA 2026.2.
- Other NVDA users have installed and used it and report that it works well.
- The Python unit tests (storage, selection and quiz logic) pass.
