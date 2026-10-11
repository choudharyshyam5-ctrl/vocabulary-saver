"""Native, labelled wx controls. No web view, custom drawing, or mouse-only UI."""
import wx
import gui
from gui import guiHelper
from logHandler import log
from .storage import DataError
from .quiz import make_questions, QuizError
from .quizDialogs import QuizDialog, ResultDialog
from .settings import quiz_options
import ui


def error_message(parent, error):
    gui.messageBox(str(error), 'Vocabulary Saver', wx.OK | wx.ICON_ERROR, parent=parent)


class EntryDialog(wx.Dialog):
    def __init__(self, parent, lessons, initial_lesson=0, word='', entry=None):
        super().__init__(parent, title='Edit vocabulary' if entry else 'Add vocabulary')
        self.lessons = lessons
        outer = wx.BoxSizer(wx.VERTICAL)
        content = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        self.lesson = content.addLabeledControl('&Lesson:', wx.Choice, choices=[x['name'] for x in lessons] if lessons else ['Create a new lesson'])
        self.lesson.SetSelection(initial_lesson)
        if not lessons:
            self.new_lesson_name = content.addLabeledControl('New lesson &name:', wx.TextCtrl, value='Lesson 1')
        self.saved_lesson_id = None
        self.lesson.Enable(entry is None)  # Editing stays in the original lesson.
        self.word = content.addLabeledControl('&Word or grammar term:', wx.TextCtrl, value=entry['word'] if entry else word)
        self.meaning = content.addLabeledControl('&Meaning:', wx.TextCtrl, value=entry['meaning'] if entry else '', style=wx.TE_MULTILINE, size=(500, 90))
        self.notes = content.addLabeledControl('&Description / notes (optional):', wx.TextCtrl, value=entry['notes'] if entry else '', style=wx.TE_MULTILINE, size=(500, 130))
        content.addDialogDismissButtons(self.CreateButtonSizer(wx.OK | wx.CANCEL))
        outer.Add(content.sizer, 1, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(outer)
        self.Bind(wx.EVT_BUTTON, self._save, id=wx.ID_OK)
        self.CentreOnParent()
        wx.CallAfter(self.word.SetFocus)

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
                )
            else:
                self.saved_lesson_id = self.lessons[index]['id']
                store.put_entry(
                    self.saved_lesson_id, self.word.GetValue(),
                    self.meaning.GetValue(), self.notes.GetValue(),
                    getattr(self, 'entry_id', None),
                )
        except (OSError, DataError) as error:
            error_message(self, error)
            return
        self.EndModal(wx.ID_OK)


class ManagerDialog(wx.Dialog):
    def __init__(self, parent, store, on_closed, lesson_id=None):
        super().__init__(parent, title='Edit vocabulary list', style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.store, self.on_closed = store, on_closed
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
        backups = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [('E&xport JSON', self.export_json), ('&Import JSON', self.import_json), ('Start &quiz', self.start_quiz)]:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            backups.Add(button, 0, wx.RIGHT, 8)
        content.addItem(backups)
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
        self.lesson.SetItems([x['name'] for x in self.lesson_data])
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
        # The list says word + meaning, so browsing does not depend on visual columns.
        self.entries.SetItems([f"{x['word']} - {x['meaning'].replace(chr(10), ' ')}" for x in self.entry_data])
        if self.entry_data:
            index = next((i for i, x in enumerate(self.entry_data) if x['id'] == entry_id), 0)
            self.entries.SetSelection(index)
        self._entry_changed(None)

    def _lesson_changed(self, event):
        self._refresh_entries()

    def _entry_changed(self, event):
        entry = self.current_entry()
        self.details.ChangeValue(
            f"Word: {entry['word']}\nMeaning: {entry['meaning']}\nDescription / notes: {entry['notes']}" if entry else 'No entries in this lesson.'
        )
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
                identifier = self.store.add_lesson(dialog.GetValue())
            except (OSError, DataError) as error:
                error_message(self, error)
                return False
            self.refresh(identifier)
            self.lesson.SetFocus()
            return True
        finally:
            dialog.Destroy()
            self.child_open = False

    def on_add(self, event):
        self.add_entry()

    def add_entry(self, word=''):
        if self.child_open:
            return
        self._entry_dialog(word=word)

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

    def start_quiz(self, event=None):
        if self.child_open:
            return
        lesson = self.current_lesson()
        if lesson is None:
            error_message(self, 'Create a lesson and add at least two distinct meanings first.')
            return
        try:
            question_count, announce_questions = quiz_options()
            questions = make_questions(lesson, question_count=question_count)
        except QuizError as error:
            error_message(self, error)
            return
        self.child_open = True
        try:
            dialog = QuizDialog(self, lesson, questions, announce_questions)
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
