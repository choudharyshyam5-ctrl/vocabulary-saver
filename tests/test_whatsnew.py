"""What's-new notice logic: when it appears and what it says. Run without NVDA."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'addon/globalPlugins/vocabularySaver/whatsnew.py'
spec = importlib.util.spec_from_file_location('vocabulary_whatsnew', MODULE)
whatsnew = importlib.util.module_from_spec(spec)
spec.loader.exec_module(whatsnew)

VERSION = '0.1.5'


class ShowDecisionTests(unittest.TestCase):
    def test_fresh_install_shows_once(self):
        # No stored version yet: the notice appears for the first start.
        self.assertTrue(whatsnew.should_show('', VERSION, True))
        self.assertTrue(whatsnew.should_show(None, VERSION, True))

    def test_same_version_never_shows_again(self):
        # After the first start the version is marked seen, so later starts stay quiet.
        self.assertFalse(whatsnew.should_show(VERSION, VERSION, True))

    def test_upgrade_from_older_release_shows(self):
        self.assertTrue(whatsnew.should_show('0.1.1', VERSION, True))

    def test_upgrade_from_dev_build_shows(self):
        self.assertTrue(whatsnew.should_show('0.1.5-dev', VERSION, True))

    def test_settings_switch_turns_it_off(self):
        self.assertFalse(whatsnew.should_show('', VERSION, False))
        self.assertFalse(whatsnew.should_show('0.1.1', VERSION, False))

    def test_empty_current_version_never_shows(self):
        self.assertFalse(whatsnew.should_show('', '', True))


class ContentTests(unittest.TestCase):
    def test_version_comes_from_the_manifest(self):
        # Guards drift: the notice must announce the version being released.
        self.assertEqual(whatsnew.current_version(), VERSION)

    def test_feedback_link_is_the_telegram_channel(self):
        self.assertEqual(whatsnew.FEEDBACK_URL, 'https://t.me/VocabularySaverNVDA')
        self.assertTrue(whatsnew.FEEDBACK_URL.startswith('https://t.me/'))

    def test_notice_names_version_link_and_shortcuts(self):
        text = whatsnew.notice_text(VERSION)
        self.assertIn(VERSION, text)
        self.assertIn('NVDA+Alt+V', text)
        self.assertIn('NVDA+Alt+B', text)
        self.assertIn('NVDA+Alt+Q', text)
        self.assertIn('Telegram', text)

    def test_notice_states_privacy_and_off_switch(self):
        text = whatsnew.notice_text(VERSION)
        self.assertIn('no network connection', text)
        self.assertIn('NVDA Settings', text)
        self.assertIn('once per version', text)

    def test_feedback_button_label(self):
        self.assertIn('Telegram', whatsnew.FEEDBACK_LABEL)


if __name__ == '__main__':
    unittest.main()
