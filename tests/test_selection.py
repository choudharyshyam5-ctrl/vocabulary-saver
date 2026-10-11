"""Selection unit tests use NVDA stubs, not live applications."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'addon/globalPlugins/vocabularySaver/selection.py'


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.api = types.SimpleNamespace(getFocusObject=lambda: None)
        self.text_infos = types.SimpleNamespace(POSITION_SELECTION='selection')
        self.modules = patch.dict(sys.modules, {'api': self.api, 'textInfos': self.text_infos})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        spec = importlib.util.spec_from_file_location('selection_under_test', MODULE)
        self.selection = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.selection)

    def focus(self, text='', collapsed=False, interceptor=None):
        obj = types.SimpleNamespace(
            treeInterceptor=interceptor,
            makeTextInfo=lambda position: types.SimpleNamespace(text=text, isCollapsed=collapsed),
        )
        self.api.getFocusObject = lambda: obj
        return obj

    def test_missing_focus(self):
        self.assertEqual(self.selection.get_selected_word(), '')

    def test_native_selection(self):
        self.focus('  猫  ')
        self.assertEqual(self.selection.get_selected_word(), '猫')

    def test_collapsed_selection(self):
        self.focus('word', collapsed=True)
        self.assertEqual(self.selection.get_selected_word(), '')

    def test_unsupported_selection(self):
        obj = self.focus()
        def unavailable(position):
            raise NotImplementedError
        obj.makeTextInfo = unavailable
        self.assertEqual(self.selection.get_selected_word(), '')

    def test_browse_mode(self):
        interceptor = types.SimpleNamespace(
            isReady=True, passThrough=False,
            makeTextInfo=lambda position: types.SimpleNamespace(text='browse', isCollapsed=False),
        )
        self.focus('native', interceptor=interceptor)
        self.assertEqual(self.selection.get_selected_word(), 'browse')

    def test_pass_through_keeps_native(self):
        self.focus('native', interceptor=types.SimpleNamespace(isReady=True, passThrough=True))
        self.assertEqual(self.selection.get_selected_word(), 'native')

    def test_long_selection_not_truncated(self):
        self.focus('x' * 201)
        self.assertEqual(self.selection.get_selected_word(), '')

    def test_200_characters_allowed(self):
        self.focus('x' * 200)
        self.assertEqual(len(self.selection.get_selected_word()), 200)


if __name__ == '__main__':
    unittest.main()
