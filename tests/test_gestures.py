"""Global hotkey tests run without NVDA or wx by parsing the plugin source.

They guard the three documented shortcuts and catch a gesture pointing at a
script method that does not exist, which would crash NVDA at runtime.
"""
import ast
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'addon/globalPlugins/vocabularySaver/__init__.py'
TREE = ast.parse(MODULE.read_text(encoding='utf-8'))


def plugin_class():
    for node in TREE.body:
        if isinstance(node, ast.ClassDef) and node.name == 'GlobalPlugin':
            return node
    raise AssertionError('GlobalPlugin class not found')


def gestures():
    for node in plugin_class().body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == '__gestures' for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError('__gestures not found')


class GestureTests(unittest.TestCase):
    EXPECTED = {
        'kb:NVDA+alt+v': 'addVocabulary',
        'kb:NVDA+alt+b': 'browseVocabulary',
        'kb:NVDA+alt+q': 'startQuiz',
    }

    def test_exact_gesture_map(self):
        self.assertEqual(gestures(), self.EXPECTED)

    def test_no_shift_v_shortcut(self):
        # NVDA+Shift+V was dropped: it clashes with Vision Assistant Pro.
        for gesture in gestures():
            self.assertNotIn('shift+v', gesture.lower())

    def test_every_gesture_has_a_script(self):
        methods = {node.name for node in plugin_class().body if isinstance(node, ast.FunctionDef)}
        for script_name in gestures().values():
            self.assertIn('script_' + script_name, methods)

    def test_no_duplicate_gestures(self):
        keys = list(gestures())
        self.assertEqual(len(keys), len(set(keys)))


if __name__ == '__main__':
    unittest.main()
