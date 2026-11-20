"""Native, labelled wx controls. No web view, custom drawing, or mouse-only UI."""
import api
import wx
import gui
from gui import guiHelper
from logHandler import log
from .storage import DataError
from .quiz import make_questions, QuizError
from .quizDialogs import QuizDialog, ResultDialog
from .settings import quiz_options, speak_readings
from .romaji import ConversionSession, detect_lookup_language, has_japanese_script, has_kana, to_romaji
from . import ai_check
from . import dict_lookup
from . import nvda_speech
from . import speakplan
import threading
import ui


def error_message(parent, error):
    gui.messageBox(str(error), 'Vocabulary Saver', wx.OK | wx.ICON_ERROR, parent=parent)


def lesson_label(lesson):
    """Name plus its optional exam/level label, so lists stay meaningful in speech."""
    return f"{lesson['name']} [{lesson['level']}]" if lesson.get('level') else lesson['name']


def reading_suffix(entry, japanese=False):
    """' (reading)' after a word, with romaji for Japanese, or '' when no reading.

    The romaji form keeps the word readable for a voice that cannot speak
    Japanese characters at all.
    """
    reading = entry.get('reading') or ''
    if not reading or reading == entry['word']:
        return ''
    romaji_text = to_romaji(reading) if japanese and has_kana(reading) else ''
    return f' ({reading}, {romaji_text})' if romaji_text else f' ({reading})'


def entry_line(entry, japanese=False):
    """One list row: word with reading, then the meaning on one line."""
    return f"{entry['word']}{reading_suffix(entry, japanese)} - {entry['meaning'].replace(chr(10), ' ')}"


def details_text(entry, japanese=False):
    if not entry:
        return 'No entries in this lesson.'
    lines = [f"Word: {entry['word']}"]
    reading = entry.get('reading') or ''
    if reading:
        romaji_text = to_romaji(reading) if japanese and has_kana(reading) else ''
        lines.append(f"Reading: {reading} ({romaji_text})" if romaji_text else f"Reading: {reading}")
    lines.append(f"Meaning: {entry['meaning']}")
    lines.append(f"Description / notes: {entry['notes']}")
    return '\n'.join(lines)


class EntryDialog(wx.Dialog):
    def __init__(self, parent, lessons, initial_lesson=0, word='', entry=None):
        super().__init__(parent, title='Edit vocabulary' if entry else 'Add vocabulary')
        self.lessons = lessons
        outer = wx.BoxSizer(wx.VERTICAL)
        content = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        content.addLabeledControl(
            '&Instructions (read only):', wx.TextCtrl,
            value='Save the word in the language you are learning, and its meaning in the language you prefer, '
                  'for example Hindi or English. The multiple-choice quiz asks for the meaning, '
                  'shown exactly as you save it here.',
            style=wx.TE_MULTILINE | wx.TE_READONLY, size=(500, 70),
        )
        self.lesson = content.addLabeledControl('&Lesson:', wx.Choice, choices=[lesson_label(x) for x in lessons] if lessons else ['Create a new lesson'])
        self.lesson.SetSelection(initial_lesson)
        if not lessons:
            self.new_lesson_name = content.addLabeledControl('New lesson &name:', wx.TextCtrl, value='Lesson 1')
        self.saved_lesson_id = None
        self.lesson.Enable(entry is None)  # Editing stays in the original lesson.
        self.word = content.addLabeledControl('&Word or grammar term:', wx.TextCtrl, value=entry['word'] if entry else word)
        self.reading = content.addLabeledControl(
            'Re&ading in hiragana (optional; shown and spoken after a Japanese word):',
            wx.TextCtrl, value=entry['reading'] if entry else '',
        )
        self.meaning = content.addLabeledControl('&Meaning:', wx.TextCtrl, value=entry['meaning'] if entry else '', style=wx.TE_MULTILINE, size=(500, 90))
        self.notes = content.addLabeledControl('&Description / notes (optional):', wx.TextCtrl, value=entry['notes'] if entry else '', style=wx.TE_MULTILINE, size=(500, 130))
        self.convert_romaji = wx.CheckBox(self, label='&Convert romaji to hiragana in the word field (Japanese lessons)')
        self.convert_romaji.SetValue(True)
        content.addItem(self.convert_romaji)
        self.undo_button = wx.Button(self, label='&Undo romaji conversion')
        self.undo_button.Bind(wx.EVT_BUTTON, self.undo_conversion)
        self.undo_button.Enable(False)
        content.addItem(self.undo_button)
        self._converting = False
        self._session = ConversionSession(self.word.GetValue())
        content.addDialogDismissButtons(self.CreateButtonSizer(wx.OK | wx.CANCEL))
        outer.Add(content.sizer, 1, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(outer)
        self.Bind(wx.EVT_BUTTON, self._save, id=wx.ID_OK)
        self.CentreOnParent()
        self.Bind(wx.EVT_TEXT, self._word_typed, self.word)
        self.word.Bind(wx.EVT_KILL_FOCUS, self._word_finished)
        wx.CallAfter(self.word.SetFocus)

    def _language_names(self):
        try:
            return {x['id']: x['name'] for x in self.GetParent().store.languages}
        except AttributeError:
            return {}

    def _current_language_name(self):
        names = self._language_names()
        if self.lessons:
            index = self.lesson.GetSelection()
            if index != wx.NOT_FOUND:
                return names.get(self.lessons[index].get('languageId'), '')
        return names.get(getattr(self.GetParent(), 'default_language_id', None), '')

    def _conversion_active(self):
        return self.convert_romaji.GetValue() and self._current_language_name().casefold() == 'japanese'

    def _apply_converted(self, old_value, new_value):
        # ChangeValue, not SetValue: keeps this a user-visible edit. The caret
        # keeps its distance from the end of the field.
        self._converting = True
        try:
            tail = len(old_value) - self.word.GetInsertionPoint()
            self.word.ChangeValue(new_value)
            self.word.SetInsertionPoint(max(0, len(new_value) - tail))
        finally:
            self._converting = False

    def undo_conversion(self, event):
        # Restore the exact romaji the user typed (raw buffer), or, after edits
        # like deletions that break raw tracking, the exact field text from
        # before the most recent automatic conversion (one step).
        value = self.word.GetValue()
        restored, _ = self._session.undo()
        if restored == value:
            return  # Nothing was converted; nothing to undo.
        self._converting = True
        try:
            self.word.ChangeValue(restored)
            self.word.SetInsertionPointEnd()
        finally:
            self._converting = False
        # The restored romaji would instantly reconvert, so undo turns
        # conversion off; the user can re-enable it with the checkbox.
        self.convert_romaji.SetValue(False)
        self.undo_button.Enable(False)
        self.word.SetFocus()

    def _word_typed(self, event):
        event.Skip()
        if self._converting:
            return
        value = self.word.GetValue()
        converted = self._session.user_edit(value, convert=self._conversion_active())
        if converted != value:
            self._apply_converted(value, converted)
            self.undo_button.Enable(True)

    def _word_finished(self, event):
        event.Skip()
        if not self._conversion_active():
            return
        value = self.word.GetValue()
        converted = self._session.user_finalize()
        if converted != value:
            self._apply_converted(value, converted)
            self.undo_button.Enable(True)

    def _save(self, event):
        # Keep this dialog open on a failed disk write; do not lose typed text.
        index = self.lesson.GetSelection()
        if index == wx.NOT_FOUND:
            error_message(self, 'Choose a lesson.')
            self.lesson.SetFocus()
            return
        try:
            store = self.GetParent().store
            if not self.lessons:
                self.saved_lesson_id, _ = store.add_lesson_with_entry(
                    self.new_lesson_name.GetValue(), self.word.GetValue(),
                    self.meaning.GetValue(), self.notes.GetValue(),
                    language_id=getattr(self.GetParent(), 'default_language_id', None),
                    reading=self.reading.GetValue(),
                )
            else:
                self.saved_lesson_id = self.lessons[index]['id']
                store.put_entry(
                    self.saved_lesson_id, self.word.GetValue(),
                    self.meaning.GetValue(), self.notes.GetValue(),
                    getattr(self, 'entry_id', None),
                    reading=self.reading.GetValue(),
                )
        except (OSError, DataError) as error:
            error_message(self, error)
            return
        self._session = ConversionSession()
        self.EndModal(wx.ID_OK)


class ManagerDialog(wx.Dialog):
    def __init__(self, parent, store, on_closed, lesson_id=None, default_language_id=None):
        super().__init__(parent, title='Edit vocabulary list', style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.store, self.on_closed = store, on_closed
        self.default_language_id = default_language_id
        self.child_open = False
        self._closed = False
        outer = wx.BoxSizer(wx.VERTICAL)
        content = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        self.lesson = content.addLabeledControl('&Lessons:', wx.Choice, choices=[])
        self.entries = content.addLabeledControl('&Words:', wx.ListBox, choices=[], size=(540, 170))
        self.details = content.addLabeledControl('&Full entry details:', wx.TextCtrl, value='', style=wx.TE_MULTILINE | wx.TE_READONLY, size=(540, 160))
        actions = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [('&New lesson', self.new_lesson), ('&Add entry', self.on_add), ('&Edit entry', self.edit_entry), ('&Delete entry', self.delete_entry)]:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            actions.Add(button, 0, wx.RIGHT, 8)
            if handler == self.edit_entry:
                self.edit_button = button
            elif handler == self.delete_entry:
                self.delete_button = button
        content.addItem(actions)
        organize = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [('Set langua&ge...', self.set_language), ('Set le&vel...', self.set_level)]:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            organize.Add(button, 0, wx.RIGHT, 8)
            if handler == self.set_language:
                self.language_button = button
            else:
                self.level_button = button
        content.addItem(organize)
        backups = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [('Search &word...', self.search_word), ('E&xport JSON', self.export_json), ('&Import JSON', self.import_json), ('Start &quiz', self.start_quiz), ('Quiz this le&vel', self.quiz_level)]:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            backups.Add(button, 0, wx.RIGHT, 8)
            if handler == self.quiz_level:
                self.level_quiz_button = button
        content.addItem(backups)
        tools = wx.BoxSizer(wx.HORIZONTAL)
        ai_button = wx.Button(self, label='Check with &AI...')
        ai_button.Bind(wx.EVT_BUTTON, self.check_with_ai)
        tools.Add(ai_button, 0, wx.RIGHT, 8)
        content.addItem(tools)
        content.addDialogDismissButtons(self.CreateButtonSizer(wx.CLOSE))
        outer.Add(content.sizer, 1, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(outer)
        self.SetMinSize(self.GetSize())
        self.Bind(wx.EVT_CHOICE, self._lesson_changed, self.lesson)
        self.Bind(wx.EVT_LISTBOX, self._entry_changed, self.entries)
        self.Bind(wx.EVT_BUTTON, self._close, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_CLOSE, self._close)
        self.Bind(wx.EVT_CHAR_HOOK, self._key)
        self.refresh(lesson_id)
        self.CentreOnParent()
        wx.CallAfter(self.lesson.SetFocus)

    def _key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE and not self.child_open:
            self.Close()
        else:
            event.Skip()

    def _close(self, event):
        if self.child_open:
            # Native modal children must close first.
            if isinstance(event, wx.CloseEvent) and event.CanVeto():
                event.Veto()
            return
        if not self._closed:
            self._closed = True
            self.on_closed()
            if self.IsModal():
                self.EndModal(wx.ID_CLOSE)
            else:
                self.Destroy()

    def refresh(self, lesson_id=None, entry_id=None):
        self.lesson_data = self.store.lessons
        self.lesson.SetItems([lesson_label(x) for x in self.lesson_data])
        if self.lesson_data:
            index = next((i for i, x in enumerate(self.lesson_data) if x['id'] == lesson_id), 0)
            self.lesson.SetSelection(index)
        self._refresh_entries(entry_id)

    def current_lesson(self):
        index = self.lesson.GetSelection()
        return self.lesson_data[index] if index != wx.NOT_FOUND else None

    def current_entry(self):
        index = self.entries.GetSelection()
        return self.entry_data[index] if index != wx.NOT_FOUND else None

    def _refresh_entries(self, entry_id=None):
        lesson = self.current_lesson()
        self.entry_data = lesson['entries'] if lesson else []
        japanese = self._current_lesson_japanese()
        # The list says word + reading + meaning, so browsing does not depend on visual columns.
        self.entries.SetItems([entry_line(x, japanese) for x in self.entry_data])
        if self.entry_data:
            index = next((i for i, x in enumerate(self.entry_data) if x['id'] == entry_id), 0)
            self.entries.SetSelection(index)
        self.language_button.Enable(lesson is not None)
        self.level_button.Enable(lesson is not None)
        self.level_quiz_button.Enable(bool(lesson and lesson.get('level')))
        self._entry_changed(None)

    def _current_lesson_japanese(self):
        lesson = self.current_lesson()
        if not lesson:
            return False
        name = next((x['name'] for x in self.store.languages if x['id'] == lesson['languageId']), '')
        return name.casefold() == 'japanese'

    def _lesson_language_name(self, lesson):
        if not lesson:
            return ''
        return next((x['name'] for x in self.store.languages if x['id'] == lesson['languageId']), '')

    def _lesson_changed(self, event):
        self._refresh_entries()

    def _entry_changed(self, event):
        entry = self.current_entry()
        self.details.ChangeValue(details_text(entry, self._current_lesson_japanese()))
        self.edit_button.Enable(entry is not None)
        self.delete_button.Enable(entry is not None)

    def new_lesson(self, event=None):
        if self.child_open:
            return False
        self.child_open = True
        dialog = wx.TextEntryDialog(self, 'Lesson name:', 'New lesson', value=f'Lesson {len(self.lesson_data) + 1}')
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return False
            try:
                identifier = self.store.add_lesson(dialog.GetValue(), language_id=self.default_language_id)
            except (OSError, DataError) as error:
                error_message(self, error)
                return False
            self.refresh(identifier)
            self.lesson.SetFocus()
            return True
        finally:
            dialog.Destroy()
            self.child_open = False

    def set_language(self, event):
        if self.child_open:
            return
        lesson = self.current_lesson()
        if lesson is None:
            return
        languages = self.store.languages
        choices = ['Unassigned'] + [x['name'] for x in languages]
        current = 0
        for position, language in enumerate(languages, start=1):
            if language['id'] == lesson['languageId']:
                current = position
                break
        self.child_open = True
        chooser = wx.SingleChoiceDialog(self, 'Assign this lesson to a language:', 'Set language', choices)
        chooser.SetSelection(current)
        try:
            if chooser.ShowModal() != wx.ID_OK:
                return
            selection = chooser.GetSelection()
            language_id = None if selection == 0 else languages[selection - 1]['id']
            try:
                self.store.set_lesson_language(lesson['id'], language_id)
            except (OSError, DataError) as error:
                error_message(self, error)
                return
            self.refresh(lesson['id'])
        finally:
            chooser.Destroy()
            self.child_open = False
            self.lesson.SetFocus()

    def set_level(self, event):
        if self.child_open:
            return
        lesson = self.current_lesson()
        if lesson is None:
            return
        self.child_open = True
        dialog = wx.TextEntryDialog(
            self, 'Exam or level label (for example JLPT N5). Leave empty to clear:', 'Set level',
            value=lesson.get('level', ''),
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            try:
                self.store.set_lesson_level(lesson['id'], dialog.GetValue())
            except (OSError, DataError) as error:
                error_message(self, error)
                return
            self.refresh(lesson['id'])
        finally:
            dialog.Destroy()
            self.child_open = False
            self.lesson.SetFocus()

    def on_add(self, event):
        self.add_entry()

    def add_entry(self, word=''):
        if self.child_open:
            return
        self._entry_dialog(word=word)

    def search_word(self, event=None):
        if self.child_open:
            return
        if not self.lesson_data:
            error_message(self, 'No lessons here yet. Create a lesson first.')
            return
        self.child_open = True
        index = self.lesson.GetSelection()
        dialog = SearchDialog(self, self.lesson_data, index if index != wx.NOT_FOUND else 0)
        try:
            if dialog.ShowModal() == wx.ID_OK:
                current = self.lesson.GetSelection()
                self.refresh(self.lesson_data[current]['id'] if current != wx.NOT_FOUND else None)
        finally:
            dialog.Destroy()
            self.child_open = False

    def edit_entry(self, event):
        entry = self.current_entry()
        if entry is not None:
            self._entry_dialog(entry=entry)

    def _entry_dialog(self, word='', entry=None):
        if self.child_open:
            return
        self.child_open = True
        index = self.lesson.GetSelection()
        dialog = EntryDialog(self, self.lesson_data, index if index != wx.NOT_FOUND else 0, word, entry)
        if entry:
            dialog.entry_id = entry['id']
        try:
            if dialog.ShowModal() == wx.ID_OK:
                chosen_id = dialog.saved_lesson_id
                self.refresh(chosen_id, entry['id'] if entry else None)
        finally:
            dialog.Destroy()
            self.child_open = False
            self.entries.SetFocus()

    def delete_entry(self, event):
        if self.child_open:
            return
        entry, lesson = self.current_entry(), self.current_lesson()
        if entry is None:
            return
        self.child_open = True
        try:
            if gui.messageBox(f"Delete '{entry['word']}' from {lesson['name']}?", 'Delete entry', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, parent=self) != wx.YES:
                return
            try:
                self.store.delete_entry(lesson['id'], entry['id'])
            except (OSError, DataError) as error:
                error_message(self, error)
                return
            self.refresh(lesson['id'])
            self.entries.SetFocus()
        finally:
            self.child_open = False

    def export_json(self, event):
        self._file_action(False)

    def import_json(self, event):
        self._file_action(True)

    def _file_action(self, importing):
        if self.child_open:
            return
        self.child_open = True
        style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST if importing else wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        dialog = wx.FileDialog(self, 'Import vocabulary' if importing else 'Export vocabulary', defaultFile='vocabulary-backup.json', wildcard='JSON files (*.json)|*.json', style=style)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = dialog.GetPath()
            if importing:
                if gui.messageBox(
                    'Import replaces ALL current lessons and entries, not a merge. '
                    'A before-import recovery copy will be saved locally. Continue?',
                    'Replace vocabulary?', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, parent=self,
                ) != wx.YES:
                    return
            try:
                if importing:
                    self.store.import_replace(path)
                    self.refresh()
                else:
                    self.store.export(path)
            except (OSError, DataError) as error:
                log.error('Vocabulary Saver backup action failed', exc_info=True)
                error_message(self, error)
                return
            gui.messageBox('Import complete.' if importing else 'Export complete.', 'Vocabulary Saver', wx.OK | wx.ICON_INFORMATION, parent=self)
        finally:
            dialog.Destroy()
            self.child_open = False

    def _run_quiz(self, quiz_lesson, language_name=''):
        try:
            question_count, announce_questions = quiz_options()
            questions = make_questions(quiz_lesson, question_count=question_count)
        except QuizError as error:
            error_message(self, error)
            return
        self.child_open = True
        try:
            dialog = QuizDialog(self, quiz_lesson, questions, announce_questions, language_name=language_name)
            try:
                result = dialog.result if dialog.ShowModal() == wx.ID_OK else None
            finally:
                dialog.Destroy()
            if result:
                ui.message(result)
                result_dialog = ResultDialog(self, result)
                try:
                    result_dialog.ShowModal()
                finally:
                    result_dialog.Destroy()
        finally:
            self.child_open = False
            self.entries.SetFocus()

    def start_quiz(self, event=None):
        if self.child_open:
            return
        lesson = self.current_lesson()
        if lesson is None:
            error_message(self, 'Create a lesson and add at least two distinct meanings first.')
            return
        self._run_quiz(lesson, self._lesson_language_name(lesson))

    def check_with_ai(self, event=None):
        if self.child_open:
            return
        if not any(lesson['entries'] for lesson in self.lesson_data):
            error_message(self, 'Add some words first, then the AI can check them.')
            return
        self.child_open = True
        try:
            dialog = AiCheckDialog(self, self.store, lambda: self.refresh())
            try:
                dialog.ShowModal()
            finally:
                dialog.Destroy()
        finally:
            self.child_open = False

    def quiz_level(self, event=None):
        """Quiz across every lesson sharing this lesson's language and exam/level."""
        if self.child_open:
            return
        lesson = self.current_lesson()
        if lesson is None or not lesson.get('level'):
            error_message(self, 'Set an exam/level label on this lesson first (Set level).')
            return
        peers = [
            x for x in self.store.lessons
            if x['languageId'] == lesson['languageId'] and x.get('level') == lesson['level']
        ]
        entries = [entry for peer in peers for entry in peer['entries']]
        language = next((x for x in self.store.languages if x['id'] == lesson['languageId']), None)
        scope = f"{language['name']} " if language else ''
        self._run_quiz({'name': f'{scope}{lesson["level"]} (all lessons)', 'entries': entries},
                       language['name'] if language else '')
class SearchDialog(wx.Dialog):
    """Look up a word online and save the chosen meaning and example as an entry."""

    def __init__(self, parent, lessons, initial_lesson=0):
        super().__init__(parent, title='Search word and add')
        self.lessons = lessons
        self._result = None
        self._examples = []
        outer = wx.BoxSizer(wx.VERTICAL)
        content = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        content.addLabeledControl(
            '&Instructions (read only):', wx.TextCtrl,
            value='Type an English or a Japanese word (kanji, kana or romaji) and press Search: the '
                  'language is detected automatically. Meanings come from an online dictionary: internet '
                  'is required and the searched word is sent to that service. Then choose the meaning and '
                  'an example sentence to save.',
            style=wx.TE_MULTILINE | wx.TE_READONLY, size=(500, 80),
        )
        self.lesson = content.addLabeledControl('&Lesson:', wx.Choice, choices=[lesson_label(x) for x in lessons])
        self.lesson.SetSelection(initial_lesson)
        self.word = content.addLabeledControl('&Word to search:', wx.TextCtrl, value='')
        self.search_button = wx.Button(self, label='&Search')
        self.search_button.Bind(wx.EVT_BUTTON, self.on_search)
        content.addItem(self.search_button)
        self.results = content.addLabeledControl(
            '&Results (read only):', wx.TextCtrl, value='No search yet.',
            style=wx.TE_MULTILINE | wx.TE_READONLY, size=(500, 160),
        )
        self.meaning = content.addLabeledControl('&Meaning to save:', wx.Choice, choices=[])
        self.example = content.addLabeledControl('&Example sentence (optional):', wx.Choice, choices=[])
        self.add_button = wx.Button(self, label='&Add to dictionary')
        self.add_button.Bind(wx.EVT_BUTTON, self.on_add)
        self.add_button.Enable(False)
        content.addItem(self.add_button)
        content.addDialogDismissButtons(self.CreateButtonSizer(wx.CANCEL))
        outer.Add(content.sizer, 1, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(outer)
        self.CentreOnParent()
        wx.CallAfter(self.word.SetFocus)

    def _language_name(self):
        try:
            names = {x['id']: x['name'] for x in self.GetParent().store.languages}
        except AttributeError:
            return ''
        index = self.lesson.GetSelection()
        if index != wx.NOT_FOUND:
            return names.get(self.lessons[index].get('languageId'), '')
        return ''

    def _set_results(self, text):
        try:
            self.results.ChangeValue(text)
        except RuntimeError:
            pass  # Dialog closed while the lookup was still running.

    def on_search(self, event):
        word = self.word.GetValue().strip()
        if not word:
            error_message(self, 'Type a word to search.')
            self.word.SetFocus()
            return
        if self.lesson.GetSelection() == wx.NOT_FOUND:
            error_message(self, 'Choose a lesson.')
            self.lesson.SetFocus()
            return
        # The script decides the dictionary, not a separate language step:
        # kanji/kana always search Japanese; Latin letters search English,
        # except in a Japanese lesson where they are tried as romaji first.
        language = detect_lookup_language(word, self._language_name())
        japanese_script = has_japanese_script(word)
        self.search_button.Enable(False)
        self.add_button.Enable(False)
        self._set_results(f'Searching for "{word}"...')

        def worker():
            try:
                if language == 'japanese':
                    try:
                        result = dict_lookup.lookup_japanese(word)
                        try:
                            examples = dict_lookup.lookup_japanese_examples(word)
                        except dict_lookup.LookupError:
                            examples = {'source': '', 'examples': []}
                    except dict_lookup.LookupError:
                        if japanese_script:
                            raise
                        # A romaji query may actually be an English word.
                        result, examples = self._english_lookup(word)
                else:
                    result, examples = self._english_lookup(word)
            except dict_lookup.LookupError as error:
                wx.CallAfter(self._show_error, word, error)
                return
            wx.CallAfter(self._show_result, result, examples)

        threading.Thread(target=worker, daemon=True).start()

    def _english_lookup(self, word):
        result = dict_lookup.lookup_english(word)
        source = result['source']
        examples = list(result['entries'][0].get('examples', []))
        try:
            tatoeba = dict_lookup.lookup_english_examples(word)
        except dict_lookup.LookupError:
            tatoeba = {'source': '', 'examples': []}
        if tatoeba['examples']:
            source += ' and Tatoeba (CC BY 2.0 FR)'
            examples += tatoeba['examples']
        return result, {'source': source, 'examples': examples}

    def _show_error(self, word, error):
        message = {
            'offline': f'Could not reach the dictionary service while searching "{word}". '
                       'Check the internet connection and try again. Nothing was saved.',
            'not_found': f'No dictionary entry found for "{word}". Nothing was saved.',
            'bad_response': f'The dictionary service returned an unreadable response for "{word}". Nothing was saved.',
        }.get(str(error), f'Lookup failed for "{word}". Nothing was saved.')
        self._set_results(message)
        self.search_button.Enable(True)

    def _show_result(self, result, examples):
        self._result = result
        entry = result['entries'][0]
        self._examples = examples.get('examples', [])
        lines = [f"Meanings source: {result['source']}"]
        heading = entry['word']
        if entry.get('reading') and entry['reading'] != entry['word']:
            heading += f" ({entry['reading']})"
        if entry.get('jlpt'):
            heading += f" [{entry['jlpt']}]"
        lines.append(heading)
        lines.append(f"Will save the word as: {entry['word']}")
        lines.append('Meanings:')
        lines += [f'  {i + 1}. {m}' for i, m in enumerate(entry['meanings'])]
        if self._examples:
            lines.append(f"Example sentences source: {examples['source']}")
            for i, x in enumerate(self._examples):
                lines.append(f'  {i + 1}. {self._format_example(x)}')
                if isinstance(x, dict):
                    lines.append(f'     {dict_lookup.tatoeba_attribution(x)}')
        else:
            lines.append('No example sentences found for this word.')
        self._set_results('\n'.join(lines))
        self.meaning.SetItems(entry['meanings'])
        self.meaning.SetSelection(0)
        self.example.SetItems([self._format_example(x) for x in self._examples] + ['No example'])
        self.example.SetSelection(len(self._examples))
        self.search_button.Enable(True)
        self.add_button.Enable(True)
        self.meaning.SetFocus()

    def _format_example(self, example):
        if isinstance(example, dict):
            return dict_lookup.tatoeba_example_text(example)
        return str(example)

    def _meaning_attribution(self):
        if self._result is None:
            return ''
        source = self._result.get('source', '')
        if 'Jisho' in source:
            return dict_lookup.JISHI_ATTRIBUTION
        return dict_lookup.english_attribution(self._result['entries'][0])

    def _compose_notes(self):
        # Meaning and example attribution travel with the entry so saved and
        # exported data keep their source credit.
        lines = []
        example_index = self.example.GetSelection()
        if 0 <= example_index < len(self._examples):
            example = self._examples[example_index]
            if isinstance(example, dict):
                lines += [dict_lookup.tatoeba_example_text(example), dict_lookup.tatoeba_attribution(example)]
            else:
                lines.append(str(example))
        lines.append(self._meaning_attribution())
        return '\n'.join(lines)

    def on_add(self, event):
        index = self.lesson.GetSelection()
        meaning_index = self.meaning.GetSelection()
        if index == wx.NOT_FOUND or meaning_index == wx.NOT_FOUND or self._result is None:
            error_message(self, 'Search first, then choose a meaning.')
            return
        notes = self._compose_notes()
        entry = self._result['entries'][0]
        store = self.GetParent().store
        lesson_id = self.lessons[index]['id']
        meaning_text = self.meaning.GetString(meaning_index)
        # Never silently overwrite: a same-word entry needs an explicit choice.
        existing = None
        for lesson in store.lessons:
            if lesson['id'] == lesson_id:
                existing = next((x for x in lesson['entries'] if x['word'].casefold() == entry['word'].casefold()), None)
        entry_id = None
        if existing is not None:
            choice = gui.messageBox(
                f'"{entry["word"]}" is already in this lesson.\n\n'
                'Yes: add as a separate new entry.\n'
                'No: update the existing entry - its current meaning and notes will be replaced.\n'
                'Cancel: do not save anything.',
                'Vocabulary Saver', wx.YES_NO | wx.CANCEL | wx.ICON_WARNING, parent=self,
            )
            if choice == wx.CANCEL:
                return
            if choice == wx.NO:
                entry_id = existing['id']
        try:
            store.put_entry(lesson_id, entry['word'], meaning_text, notes, entry_id,
                            reading=entry.get('reading', ''))
        except (OSError, DataError) as error:
            error_message(self, error)
            return
        self.EndModal(wx.ID_OK)


class AiCheckDialog(wx.Dialog):
    """Copy-paste bridge to any AI chat: export the words, apply the reply.

    The add-on makes no network call and needs no API key: the user copies
    the export text into an AI chat and pastes the reply back. Only readings
    and meanings are ever updated, after a confirmation that lists the counts.
    """

    def __init__(self, parent, store, on_applied):
        super().__init__(parent, title='Check vocabulary with AI', style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.store, self.on_applied = store, on_applied
        self._export_text = ai_check.build_ai_export(store.data)
        outer = wx.BoxSizer(wx.VERTICAL)
        content = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        content.addLabeledControl(
            '&How it works (read only):', wx.TextCtrl,
            value=('1. Press "Copy export text". 2. Paste it into any AI chat, for example Gemini '
                   'or ChatGPT. 3. Copy the reply the AI gives. 4. Paste it into the reply box '
                   'below and press "Apply corrections". The add-on sends nothing anywhere by '
                   'itself: you do the copying. Only readings and meanings are updated, after '
                   'your confirmation. Words, notes and lessons are never changed.'),
            style=wx.TE_MULTILINE | wx.TE_READONLY, size=(520, 100),
        )
        self.export_text = content.addLabeledControl(
            '&Text to paste into the AI:', wx.TextCtrl, value=self._export_text,
            style=wx.TE_MULTILINE | wx.TE_READONLY, size=(520, 150),
        )
        copy_button = wx.Button(self, label='&Copy export text')
        copy_button.Bind(wx.EVT_BUTTON, self._copy)
        content.addItem(copy_button)
        self.reply = content.addLabeledControl('AI &reply (paste it here):', wx.TextCtrl, style=wx.TE_MULTILINE, size=(520, 150))
        self.apply_button = wx.Button(self, label='&Apply corrections')
        self.apply_button.Bind(wx.EVT_BUTTON, self._apply)
        content.addItem(self.apply_button)
        content.addDialogDismissButtons(self.CreateButtonSizer(wx.CLOSE))
        outer.Add(content.sizer, 1, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(outer)
        self.CentreOnParent()
        wx.CallAfter(copy_button.SetFocus)

    def _copy(self, event):
        if api.copyToClip(self._export_text):
            ui.message('Export text copied. Paste it into your AI chat.')
        else:
            gui.messageBox('Could not copy the text. Select it and copy it manually.',
                           'Check with AI', wx.OK | wx.ICON_ERROR, parent=self)

    def _apply(self, event):
        reply = self.reply.GetValue().strip()
        if not reply:
            error_message(self, 'Paste the AI reply first.')
            self.reply.SetFocus()
            return
        try:
            result = ai_check.parse_ai_reply(reply, self.store.data)
        except ai_check.AICheckError as error:
            error_message(self, error)
            self.reply.SetFocus()
            return
        patches = result['patches']
        if not patches:
            gui.messageBox(
                'The reply matches your current vocabulary: nothing to change.'
                + (f" Skipped {result['skipped']} unknown item(s)." if result['skipped'] else ''),
                'Check with AI', wx.OK | wx.ICON_INFORMATION, parent=self,
            )
            return
        summary = (f"Apply these corrections from the AI reply?\n\n"
                   f"Readings added or changed: {result['readings']}\n"
                   f"Meanings tidied: {result['meanings']}\n")
        if result['skipped']:
            summary += f"Skipped as unknown: {result['skipped']}\n"
        summary += '\nWords, notes and lessons are never changed by this step.'
        if gui.messageBox(summary, 'Apply AI corrections?', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, parent=self) != wx.YES:
            return
        try:
            applied = self.store.patch_entries(patches)
        except (OSError, DataError) as error:
            error_message(self, error)
            return
        ui.message(f'Corrections applied to {applied} entries.')
        self.on_applied()
        gui.messageBox(f'Done. {applied} entries updated.', 'Check with AI', wx.OK | wx.ICON_INFORMATION, parent=self)
