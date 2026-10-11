"""NVDA entry point. Keep scripts short and let wx handle the UI asynchronously."""
from pathlib import Path
import globalPluginHandler
import globalVars
import gui
import ui
import wx
from logHandler import log
from scriptHandler import script
from winAPI.sessionTracking import isLockScreenModeActive
from .selection import get_selected_word
from .storage import Store, DataError
from .lessonDialogs import LessonDialog
from .settings import initialize, VocabularySettingsPanel
from gui.settingsDialogs import NVDASettingsDialog


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = 'Vocabulary Saver'
    # NVDA uses __gestures, NOT __gestures__ (see its developer guide).
    __gestures = {
        'kb:NVDA+shift+v': 'addVocabulary',
        'kb:NVDA+alt+v': 'browseVocabulary',
    }

    def __init__(self):
        super().__init__()
        self._dialog = None
        self._tools_item = None
        self._menu_bindings = []
        initialize()
        if not globalVars.appArgs.secure:
            if VocabularySettingsPanel not in NVDASettingsDialog.categoryClasses:
                NVDASettingsDialog.categoryClasses.append(VocabularySettingsPanel)
            submenu = wx.Menu()
            for label, handler in [
                ('&Add vocabulary...', self._menu_add),
                ('&Read vocabulary list...', self._menu_read),
                ('&Edit vocabulary list...', self._menu_edit),
                ('Start &MCQ quiz...', self._menu_quiz),
                ('&Lessons...', self._menu_lessons),
            ]:
                item = submenu.Append(wx.ID_ANY, label)
                gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, handler, item)
                self._menu_bindings.append((item.GetId(), handler))
            self._tools_item = gui.mainFrame.sysTrayIcon.toolsMenu.AppendSubMenu(submenu, 'Vocabulary Saver')

    def _menu_add(self, event):
        wx.CallAfter(self._open, '', True)

    def _menu_read(self, event):
        wx.CallAfter(self._open, '', False, 'read')

    def _menu_edit(self, event):
        wx.CallAfter(self._open, '', False, 'edit')

    def _menu_quiz(self, event):
        wx.CallAfter(self._open, '', False, 'quiz')

    def _menu_lessons(self, event):
        wx.CallAfter(self._open)

    @script(description='Add a vocabulary entry, using selected text when available')
    def script_addVocabulary(self, gesture):
        if not globalVars.appArgs.secure and not isLockScreenModeActive():
            word = get_selected_word()
            if not word:
                ui.message('No short text selection available. Enter the word manually.')
            wx.CallAfter(self._open, word, True)

    @script(description='Browse vocabulary lessons and manage entries or backups')
    def script_browseVocabulary(self, gesture):
        if not globalVars.appArgs.secure and not isLockScreenModeActive():
            wx.CallAfter(self._open, '', False)

    def _open(self, word='', add=False, action=None):
        if globalVars.appArgs.secure or isLockScreenModeActive():
            return
        if self._dialog is not None:
            if self._dialog.child_open:
                return
            self._dialog.Raise()
            self._dialog.SetFocus()
            if add:
                wx.CallAfter(self._dialog.add_entry, word)
            elif action:
                wx.CallAfter(self._dialog.open_action, action)
            return
        try:
            path = Path(globalVars.appArgs.configPath) / 'vocabularySaver' / 'vocabulary.json'
            store = Store(path)
        except (OSError, DataError) as error:
            log.error('Vocabulary Saver could not load its data', exc_info=True)
            gui.messageBox(
                f'Cannot open vocabulary data: {error}\nThe file has not been overwritten. '
                'Keep a copy before repairing it. See the README for recovery.',
                'Vocabulary Saver', wx.OK | wx.ICON_ERROR,
            )
            return
        gui.mainFrame.prePopup()
        try:
            self._dialog = LessonDialog(gui.mainFrame, store, self._on_closed)
            self._dialog.Show()
        except Exception:
            self._dialog = None
            log.error('Vocabulary Saver dialog creation failed', exc_info=True)
            raise
        finally:
            gui.mainFrame.postPopup()
        if add:
            wx.CallAfter(self._dialog.add_entry, word)
        elif action:
            wx.CallAfter(self._dialog.open_action, action)

    def _on_closed(self):
        self._dialog = None

    def terminate(self):
        if VocabularySettingsPanel in NVDASettingsDialog.categoryClasses:
            NVDASettingsDialog.categoryClasses.remove(VocabularySettingsPanel)
        for identifier, handler in self._menu_bindings:
            gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, handler=handler, id=identifier)
        self._menu_bindings = []
        if self._tools_item is not None:
            gui.mainFrame.sysTrayIcon.toolsMenu.DestroyItem(self._tools_item)
            self._tools_item = None
        if self._dialog is not None:
            self._dialog.Destroy()
            self._dialog = None
        super().terminate()
