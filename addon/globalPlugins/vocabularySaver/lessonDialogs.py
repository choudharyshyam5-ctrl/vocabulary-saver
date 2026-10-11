"""Distinct lesson read and edit paths. Read mode has no store mutation controls."""
import wx
import gui
from gui import guiHelper
import ui
from .dialogs import ManagerDialog, error_message


class ReadDialog(wx.Dialog):
    def __init__(self, parent, lesson):
        super().__init__(parent, title=f"Read vocabulary list: {lesson['name']}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.entry_data = lesson['entries']
        outer = wx.BoxSizer(wx.VERTICAL)
        content = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        self.words = content.addLabeledControl('&Words:', wx.ListBox, choices=[f"{entry['word']} - {entry['meaning'].replace(chr(10), ' ')}" for entry in self.entry_data], size=(540, 180))
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

    def entry_text(self):
        index = self.words.GetSelection()
        if index == wx.NOT_FOUND:
            return 'No entries in this lesson.'
        entry = self.entry_data[index]
        return f"Word: {entry['word']}\nMeaning: {entry['meaning']}\nDescription / notes: {entry['notes']}"

    def update_details(self, event):
        self.details.ChangeValue(self.entry_text())

    def read_entry(self, event):
        ui.message(self.entry_text())


class LessonDialog(wx.Dialog):
    def __init__(self, parent, store, on_closed):
        super().__init__(parent, title='Vocabulary Saver: lessons')
        self.store, self.on_closed = store, on_closed
        self.child_open = False
        self._closed = False
        outer = wx.BoxSizer(wx.VERTICAL)
        content = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
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
        self.Bind(wx.EVT_BUTTON, self._close, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_CLOSE, self._close)
        self.Bind(wx.EVT_CHAR_HOOK, self._key)
        self.refresh()
        wx.CallAfter(add_button.SetFocus)

    def refresh(self, lesson_id=None):
        self.lesson_data = self.store.lessons
        self.lessons.SetItems([lesson['name'] for lesson in self.lesson_data])
        if self.lesson_data:
            index = next((i for i, lesson in enumerate(self.lesson_data) if lesson['id'] == lesson_id), 0)
            self.lessons.SetSelection(index)

    def current_lesson(self):
        index = self.lessons.GetSelection()
        return self.lesson_data[index] if index != wx.NOT_FOUND else None

    def read_list(self, event):
        if self.child_open:
            return
        lesson = self.current_lesson()
        if lesson is None:
            error_message(self, 'No lessons yet. Use Edit vocabulary list, then New lesson.')
            return
        self.child_open = True
        try:
            dialog = ReadDialog(self, lesson)
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
        if self.lesson_data:
            self.child_open = True
            chooser = wx.SingleChoiceDialog(self, 'Choose a lesson:', 'Vocabulary Saver', [lesson['name'] for lesson in self.lesson_data])
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

    def edit_list(self, event=None):
        self._edit()

    def add_entry(self, word=''):
        self._edit(word, add=True)

    def _edit(self, word='', add=False, quiz=False):
        if self.child_open:
            return
        lesson = self.current_lesson()
        lesson_id = lesson['id'] if lesson else None
        self.child_open = True
        try:
            dialog = ManagerDialog(self, self.store, lambda: None, lesson_id)
            try:
                if add:
                    wx.CallAfter(dialog.add_entry, word)
                elif quiz:
                    wx.CallAfter(dialog.start_quiz)
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
