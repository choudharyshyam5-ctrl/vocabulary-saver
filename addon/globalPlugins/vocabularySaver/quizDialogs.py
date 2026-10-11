"""Accessible MCQ practice and a score the user can copy and share themselves."""
import api
import gui
from gui import guiHelper
import ui
import wx
from .quiz import score, score_text


class ResultDialog(wx.Dialog):
    def __init__(self, parent, result):
        super().__init__(parent, title='MCQ quiz result', style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.result = result
        outer = wx.BoxSizer(wx.VERTICAL)
        content = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        self.text = content.addLabeledControl('&Score to share:', wx.TextCtrl, value=result, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(520, 160))
        copy_button = wx.Button(self, label='&Copy score')
        copy_button.Bind(wx.EVT_BUTTON, self._copy)
        content.addItem(copy_button)
        content.addDialogDismissButtons(self.CreateButtonSizer(wx.OK))
        outer.Add(content.sizer, 1, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(outer)
        self.CentreOnParent()
        wx.CallAfter(self.text.SetFocus)

    def _copy(self, event):
        if api.copyToClip(self.result):
            ui.message('Score copied. Paste it into a message to share it yourself.')
        else:
            gui.messageBox('Could not copy the score. Select the text and copy manually.', 'MCQ result', wx.OK | wx.ICON_ERROR, parent=self)


class QuizDialog(wx.Dialog):
    def __init__(self, parent, lesson, questions, announce_questions=True):
        super().__init__(parent, title='Vocabulary MCQ quiz', style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.lesson, self.questions = lesson, questions
        self.announce_questions = announce_questions
        self.answers, self.index = [], 0
        self.result = None
        outer = wx.BoxSizer(wx.VERTICAL)
        content = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        self.prompt = content.addLabeledControl('&Question:', wx.TextCtrl, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(520, 100))
        self.options = content.addLabeledControl('&Answer:', wx.Choice, choices=[], size=(520, -1))
        self.next_button = wx.Button(self, label='&Submit answer')
        self.next_button.Bind(wx.EVT_BUTTON, self._submit)
        content.addItem(self.next_button)
        content.addDialogDismissButtons(self.CreateButtonSizer(wx.CANCEL))
        outer.Add(content.sizer, 1, wx.EXPAND | wx.ALL, 12)
        self.SetSizerAndFit(outer)
        self.CentreOnParent()
        self._show_question()

    def _show_question(self):
        question = self.questions[self.index]
        value = f'Question {self.index + 1} of {len(self.questions)}. What is the meaning of {question.word}?'
        self.prompt.ChangeValue(value)
        self.options.SetItems([f'{i + 1}. {option}' for i, option in enumerate(question.options)])
        self.options.SetSelection(wx.NOT_FOUND)
        self.next_button.SetLabel('&Finish quiz' if self.index == len(self.questions) - 1 else '&Submit answer')
        wx.CallAfter(self.options.SetFocus)
        if self.announce_questions:
            wx.CallAfter(ui.message, value)

    def _submit(self, event):
        answer = self.options.GetSelection()
        if answer == wx.NOT_FOUND:
            gui.messageBox('Choose an answer using the arrow keys, then submit.', 'MCQ quiz', wx.OK | wx.ICON_INFORMATION, parent=self)
            self.options.SetFocus()
            return
        self.answers.append(answer)
        self.index += 1
        if self.index < len(self.questions):
            self._show_question()
            return
        correct = score(self.questions, self.answers)
        self.result = score_text(self.lesson['name'], correct, len(self.questions))
        self.EndModal(wx.ID_OK)
