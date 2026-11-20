"""Profile settings for local MCQ practice and spoken readings."""
import config
from gui import guiHelper
from gui.settingsDialogs import SettingsPanel
import wx

SECTION = 'vocabularySaver'
SPEC = {
    'questionCount': 'integer(default=10, min=0, max=20000)',
    'announceQuestions': 'boolean(default=True)',
    'speakReadings': 'boolean(default=True)',
    'showWhatsNew': 'boolean(default=True)',
    'lastSeenVersion': 'string(default="")',
}


def initialize():
    config.conf.spec[SECTION] = SPEC


def quiz_options():
    return config.conf[SECTION]['questionCount'], config.conf[SECTION]['announceQuestions']


def whats_new_enabled():
    """Whether the one-time what's-new notice appears after an update."""
    return config.conf[SECTION]['showWhatsNew']


def last_seen_version():
    """The add-on version the notice was last shown for, empty on a fresh install."""
    return config.conf[SECTION]['lastSeenVersion']


def mark_version_seen(version):
    config.conf[SECTION]['lastSeenVersion'] = version


def speak_readings():
    """Whether the kana reading is spoken after a word in a lesson with a language."""
    return config.conf[SECTION]['speakReadings']


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
        self.readings = wx.CheckBox(self, label='Speak the &reading after the word in lessons with a set language')
        self.readings.SetValue(speak_readings())
        helper.addItem(self.readings)
        self.whatsnew = wx.CheckBox(self, label="Show the &what's-new notice once after each update")
        self.whatsnew.SetValue(whats_new_enabled())
        helper.addItem(self.whatsnew)

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
        config.conf[SECTION]['speakReadings'] = self.readings.GetValue()
        config.conf[SECTION]['showWhatsNew'] = self.whatsnew.GetValue()
