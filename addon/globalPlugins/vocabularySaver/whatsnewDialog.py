"""The wx dialog for the one-time what's-new notice. Imported lazily, only when shown."""
import webbrowser
import wx
from .whatsnew import FEEDBACK_LABEL, FEEDBACK_URL, notice_text


class WhatsNewDialog(wx.Dialog):
    """A small dialog with the notes, a feedback button and a Close button."""

    def __init__(self, parent, version):
        super().__init__(parent, title=f'Vocabulary Saver updated to {version}')
        sizer = wx.BoxSizer(wx.VERTICAL)
        # A read-only multi-line edit: screen readers can review every line,
        # and focus starts here so the notes are the first thing announced.
        notes = wx.TextCtrl(
            self,
            value=notice_text(version),
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(480, 260),
        )
        sizer.Add(notes, proportion=1, flag=wx.EXPAND | wx.ALL, border=8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        feedback = wx.Button(self, label=FEEDBACK_LABEL)
        feedback.Bind(wx.EVT_BUTTON, self._on_feedback)
        close = wx.Button(self, wx.ID_CANCEL, label='&Close')
        buttons.Add(feedback, flag=wx.RIGHT, border=8)
        buttons.Add(close)
        sizer.Add(buttons, flag=wx.ALIGN_RIGHT | wx.ALL, border=8)
        self.SetSizerAndFit(sizer)
        self.SetEscapeId(wx.ID_CANCEL)
        notes.SetFocus()

    def _on_feedback(self, event):
        # The only network-adjacent action, and only on an explicit press.
        webbrowser.open(FEEDBACK_URL)
        self.Close()
