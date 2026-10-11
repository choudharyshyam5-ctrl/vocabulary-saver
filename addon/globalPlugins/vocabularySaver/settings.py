"""Exactly two NVDA profile settings for local MCQ practice."""
import config
from gui import guiHelper
from gui.settingsDialogs import SettingsPanel
import wx

SECTION = 'vocabularySaver'
SPEC = {
    'questionCount': 'integer(default=10, min=0, max=20000)',
    'announceQuestions': 'boolean(default=True)',
}


def initialize():
    config.conf.spec[SECTION] = SPEC


def quiz_options():
    return config.conf[SECTION]['questionCount'], config.conf[SECTION]['announceQuestions']


class VocabularySettingsPanel(SettingsPanel):
    title = 'Vocabulary Saver'

    def makeSettings(self, settingsSizer):
        helper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        count, announce = quiz_options()
        # Native editable combo: type a count, or select All from the list.
        self.count = helper.addLabeledControl(
            '&Number of questions per MCQ quiz:', wx.ComboBox,
            choices=['10', 'All'], value='All' if count == 0 else str(count),
        )
        self.announce = wx.CheckBox(self, label='&Announce each question automatically when it appears')
        self.announce.SetValue(announce)
        helper.addItem(self.announce)

    def _count_value(self):
        value = self.count.GetValue().strip()
        if value.casefold() == 'all':
            return 0
        try:
            number = int(value)
        except ValueError:
            raise ValueError('Enter a whole number from 1 to 20000, or choose All.')
        if not 1 <= number <= 20000:
            raise ValueError('Enter a whole number from 1 to 20000, or choose All.')
        return number

    def isValid(self):
        try:
            self._count_value()
        except ValueError as error:
            from gui import messageBox
            messageBox(str(error), 'Vocabulary Saver', wx.OK | wx.ICON_ERROR, parent=self)
            self.count.SetFocus()
            return False
        return True

    def onSave(self):
        config.conf[SECTION]['questionCount'] = self._count_value()
        config.conf[SECTION]['announceQuestions'] = self.announce.GetValue()
