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

## Required manual Windows/NVDA checks before a release

Record NVDA version, Windows version, keyboard layout, speech/braille settings
and each result. Use a test/portable configuration.

1. Enable development scratchpad, load plugin, restart. Check no errors in log.
2. Input Help announces both shortcuts; Input Gestures shows both descriptions.
3. First Add creates a lesson only after confirmation. Cancel creates nothing.
4. Empty word/meaning gets an announced error; typed text remains available.
5. Enter Japanese and multiline meaning/notes. Restart NVDA and confirm exact data.
6. Test selected-word capture in Notepad, a browser browse-mode selection, and
   an editor with native selection. Test no selection and a long selection.
   Ensure clipboard contents remain unchanged and manual entry still works.
7. Tab/Shift+Tab through EVERY control; verify label, role, value and focused
   item are spoken/brailled. Check Alt access keys, arrows, Enter, Space, Escape.
8. Add another lesson, choose it, save, edit, delete with No then Yes; confirm
   data is correct and focus stays in the manager. Resize and check no clipping.
9. Test speech and braille reading of the read-only details box, long meanings,
   multiline notes, empty lesson and large list. Check high-DPI display layout.
10. Export to a separate file. Add a lesson. Import the export: cancel once, then
    confirm replacement; check .before-import.json preserves previous data.
11. Import a bad JSON file or schema 2: error, no overwritten data. Set the data
    directory read-only: save must fail with an error, not report success.
12. Open Add twice quickly, or while a file picker/entry dialog is open: only one
    manager, no stranded/duplicate dialogs. Close with Escape and Close button.
13. After closing NVDA, deliberately corrupt a TEST data file; restart and open:
    visible/announced error and no silent data reset. Restore from a copy.
14. Remove scratchpad copy, build with your verified version, install externally,
    restart and repeat the basic flow. Verify installed/portable config paths.
15. Verify plugin does not expose entries or writable dialogs in secure mode.
    Any lock-screen/security regression blocks release.
16. Disable/uninstall/reload during development: no abandoned dialog or log errors.

No Windows runtime or screenshot/layout inspection has been performed here.
Do not mark a checklist item passed based only on Python compilation.

## Preparation results (11 October 2026)

- Python 3.11.16: all 12 Python files passed `py_compile`.
- Python 3.11.16: 45 storage, stubbed selection and MCQ logic unit tests passed.
- Package builder checked in a disposable copy: missing tested version rejected;
  correct archive root, included HTML help, no Python caches, ZIP integrity passed.
  Its synthetic version input was not runtime testing; that package was discarded.
- Local HTML README preview inspected: readable headings, paragraphs and list
  hierarchy. Native wx dialog visuals and NVDA announcements remain UNVERIFIED.

## MCQ manual checks

- Quiz with an empty lesson or one distinct meaning: announced error, no quiz.
- Quiz with 2, 3 and 4+ distinct meanings: correct number of answer options.
- Word with conflicting saved meanings skipped; identical duplicates asked once.
- Prompt announced and readable; answer label/options announced with arrow keys.
- Submit with no chosen option: announced message, no score change.
- Finish: correct announced score and readable plain-text result. Copy score
  changes clipboard only when pressed; paste matches visible result. No sending.
- Cancel midway: no result or vocabulary mutation. Restart: vocabulary unchanged.
- Attempt add/browse gesture during quiz: no duplicate dialog or focus theft.
- Inspect actual Windows dialog layout including long answer options/high DPI.

## Distinct read/edit paths

- NVDA+Alt+V shows lesson choice plus separate Read vocabulary list and Edit
  vocabulary list buttons. Their labels must announce clearly.
- Read mode: browse/read all entries and notes; no editable fields, data saves,
  add/delete controls, or clipboard side effects. Read selected entry speaks.
- Edit mode opens chosen lesson and preserves add/edit/delete, quiz and backup.
- NVDA+Shift+V opens edit/add directly and prefills selected text as before.
- Empty library: Read gives a clear message; Edit permits New lesson.
- Closing either child returns to the lesson chooser; editing refreshes its data.
- Gestures while a read/edit child is open must not create duplicate dialogs.
- Inspect native layout and verify keyboard/speech/braille for all new controls.

## Add vocabulary lesson dropdown

- First action is Add vocabulary; it opens Lesson dropdown before entry fields.
- Empty library: exactly one choice, Create a new lesson; Lesson name field shown.
- Save first valid entry: lesson + entry saved together. Cancel/invalid entry
  creates neither; disk error does not lose the typed entry or report success.
- Existing lessons: dropdown shows their actual names; selecting a lesson saves
  entry into that lesson. Hotkey selected-word prefill still works.

## Tools menu

- Tools > Vocabulary Saver submenu appears once, with all five named actions.
- Read/Edit/Quiz asks for the desired lesson; cancel opens no child action.
- Add menu entry follows identical empty/existing-lesson dropdown behavior.
- Disable/reload/uninstall removes submenu and handlers; no duplicate entries.
- Secure mode has no submenu; locked-session actions must not open private data.
- Test keyboard-only menu navigation and spoken/braille labels on live NVDA.

## Two settings

- Settings > Vocabulary Saver appears once and has exactly two labelled options.
- Count defaults to 10; All, 1 and another integer save; invalid text/zero is
  rejected with an announced error, leaving settings dialog open.
- Apply/OK persists; Cancel does not apply. Restart/profile changes honor settings.
- With 15 usable words: default quiz has 10; count 3 has 3; All has 15.
- Automatic announcements default on. Turn off: question text still readable,
  no automatic prompt speech; final score remains announced.
- Unloading plugin removes settings category without disturbing other categories.
