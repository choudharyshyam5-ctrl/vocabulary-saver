"""Distinct lesson read and edit paths. Read mode has no store mutation controls."""
import wx
import gui
from gui import guiHelper
import ui
from .storage import DataError
from .dialogs import ManagerDialog, error_message, lesson_label, entry_line, details_text
from .settings import speak_readings
from . import nvda_speech
from . import speakplan


class ReadDialog(wx.Dialog):
    def __init__(self, parent, lesson, language_name=''):
        super().__init__(parent, title=f"Read vocabulary list: {lesson['name']}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.entry_data = lesson['entries']
        self.language_name = language_name
        self._japanese = language_name.casefold() == 'japanese'
        outer = wx.BoxSizer(wx.VERTICAL)
        content = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        self.words = content.addLabeledControl('&Words:', wx.ListBox, choices=[entry_line(entry, self._japanese) for entry in self.entry_data], size=(540, 180))
        self.details = content.addLabeledControl('&Details (read only):', wx.TextCtrl, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(540, 170))
        read_button = wx.Button(self, label='&Read selected entry')
        read_button.Bind(wx.EVT_BUTTON, self.read_entry)
        read_button.Enable(bool(self.entry_data))
        content.addItem(read_button)
        content.addDialogDismissButtons(self.CreateButtonSizer(wx.OK))
        outer.Add(content.sizer, 1, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(outer)
        self.CentreOnParent()
        self.words.Bind(wx.EVT_LISTBOX, self.update_details)
        if self.entry_data:
            self.words.SetSelection(0)
        self.update_details(None)
        wx.CallAfter(self.words.SetFocus)

    def current_entry(self):
        index = self.words.GetSelection()
        return self.entry_data[index] if index != wx.NOT_FOUND else None

    def update_details(self, event):
        self.details.ChangeValue(details_text(self.current_entry(), self._japanese))

    def read_entry(self, event):
        entry = self.current_entry()
        if entry is None:
            ui.message('No entries in this lesson.')
            return
        # The word and its reading are spoken in the lesson's language through
        # NVDA's automatic language switching; meaning and notes stay in the
        # default voice, as they are written in the learner's own language.
        nvda_speech.speak_segments(speakplan.entry_speech_segments(
            entry, speakplan.language_code(self.language_name), speak_readings(),
        ))


class LessonDialog(wx.Dialog):
    def __init__(self, parent, store, on_closed):
        super().__init__(parent, title='Vocabulary Saver: lessons')
        self.store, self.on_closed = store, on_closed
        self.child_open = False
        self._closed = False
        self._language_marker = 'all'
        outer = wx.BoxSizer(wx.VERTICAL)
        content = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        self.languages = content.addLabeledControl('Lan&guage:', wx.Choice, choices=[])
        add_language_button = wx.Button(self, label='Add lan&guage...')
        add_language_button.Bind(wx.EVT_BUTTON, self.add_language)
        content.addItem(add_language_button)
        add_button = wx.Button(self, label='&Add vocabulary')
        add_button.Bind(wx.EVT_BUTTON, self.on_add)
        content.addItem(add_button)
        self.lessons = content.addLabeledControl('&Lesson:', wx.Choice, choices=[])
        for label, handler in [('&Read vocabulary list', self.read_list), ('&Edit vocabulary list', self.edit_list)]:
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            content.addItem(button)
        content.addDialogDismissButtons(self.CreateButtonSizer(wx.CLOSE))
        outer.Add(content.sizer, 1, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(outer)
        self.CentreOnParent()
        self.Bind(wx.EVT_CHOICE, self._language_changed, self.languages)
        self.Bind(wx.EVT_BUTTON, self._close, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_CLOSE, self._close)
        self.Bind(wx.EVT_CHAR_HOOK, self._key)
        self.refresh()
        wx.CallAfter(add_button.SetFocus)

    def _language_choices(self):
        languages = self.store.languages
        markers = ['all'] + [x['id'] for x in languages] + ['none']
        labels = ['All languages'] + [x['name'] for x in languages] + ['Unassigned lessons']
        return markers, labels

    def _filtered_lessons(self):
        lessons = self.store.lessons
        if self._language_marker == 'all':
            return lessons
        if self._language_marker == 'none':
            return [x for x in lessons if x['languageId'] is None]
        return [x for x in lessons if x['languageId'] == self._language_marker]

    def refresh(self, lesson_id=None):
        markers, labels = self._language_choices()
        if self._language_marker not in markers:
            self._language_marker = 'all'
        self.languages.SetItems(labels)
        self.languages.SetSelection(markers.index(self._language_marker))
        self.lesson_data = self._filtered_lessons()
        self.lessons.SetItems([lesson_label(lesson) for lesson in self.lesson_data])
        if self.lesson_data:
            index = next((i for i, lesson in enumerate(self.lesson_data) if lesson['id'] == lesson_id), 0)
            self.lessons.SetSelection(index)

    def _language_changed(self, event):
        markers, _ = self._language_choices()
        index = self.languages.GetSelection()
        if index != wx.NOT_FOUND:
            self._language_marker = markers[index]
        self.refresh()

    def add_language(self, event):
        if self.child_open:
            return
        self.child_open = True
        dialog = wx.TextEntryDialog(self, 'Language name:', 'Add a language', value='')
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            try:
                identifier = self.store.add_language(dialog.GetValue())
            except (OSError, DataError) as error:
                error_message(self, error)
                return
            self._language_marker = identifier
            self.refresh()
            self.languages.SetFocus()
        finally:
            dialog.Destroy()
            self.child_open = False

    def current_lesson(self):
        index = self.lessons.GetSelection()
        return self.lesson_data[index] if index != wx.NOT_FOUND else None

    def default_language_id(self):
        return self._language_marker if self._language_marker not in ('all', 'none') else None

    def read_list(self, event):
        if self.child_open:
            return
        lesson = self.current_lesson()
        if lesson is None:
            error_message(self, 'No lessons here yet. Use Edit vocabulary list, then New lesson.')
            return
        language = next((x['name'] for x in self.store.languages if x['id'] == lesson['languageId']), '')
        self.child_open = True
        try:
            dialog = ReadDialog(self, lesson, language)
            try:
                dialog.ShowModal()
            finally:
                dialog.Destroy()
        finally:
            self.child_open = False
            self.lessons.SetFocus()

    def on_add(self, event):
        self.add_entry()

    def open_action(self, action):
        if self.child_open:
            return
        # Menu actions ask for a lesson instead of silently choosing Lesson 1.
        if self.lesson_data and action != 'ai':
            self.child_open = True
            chooser = wx.SingleChoiceDialog(self, 'Choose a lesson:', 'Vocabulary Saver', [lesson_label(lesson) for lesson in self.lesson_data])
            chooser.SetSelection(self.lessons.GetSelection())
            try:
                if chooser.ShowModal() != wx.ID_OK:
                    return
                self.lessons.SetSelection(chooser.GetSelection())
            finally:
                chooser.Destroy()
                self.child_open = False
        if action == 'read':
            self.read_list(None)
        elif action == 'quiz':
            self._edit(quiz=True)
        elif action == 'edit':
            self._edit()
        elif action == 'search':
            self._edit(search=True)
        elif action == 'ai':
            self._edit(ai=True)

    def edit_list(self, event=None):
        self._edit()

    def add_entry(self, word=''):
        self._edit(word, add=True)

    def _edit(self, word='', add=False, quiz=False, search=False, ai=False):
        if self.child_open:
            return
        lesson = self.current_lesson()
        lesson_id = lesson['id'] if lesson else None
        self.child_open = True
        try:
            dialog = ManagerDialog(self, self.store, lambda: None, lesson_id, default_language_id=self.default_language_id())
            try:
                if add:
                    wx.CallAfter(dialog.add_entry, word)
                elif quiz:
                    wx.CallAfter(dialog.start_quiz)
                elif search:
                    wx.CallAfter(dialog.search_word)
                elif ai:
                    wx.CallAfter(dialog.check_with_ai)
                dialog.ShowModal()
                chosen = dialog.current_lesson()
                lesson_id = chosen['id'] if chosen else None
            finally:
                dialog.Destroy()
            self.refresh(lesson_id)
        finally:
            self.child_open = False
            self.lessons.SetFocus()

    def _key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE and not self.child_open:
            self.Close()
        else:
            event.Skip()

    def _close(self, event):
        if self.child_open:
            if isinstance(event, wx.CloseEvent) and event.CanVeto():
                event.Veto()
            return
        if not self._closed:
            self._closed = True
            self.on_closed()
            self.Destroy()
