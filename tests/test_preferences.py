import unittest

from core.keyboards.lead_settings_kb import lead_settings_keyboard
from core.leads.preferences import DEFAULT_SETTINGS, LeadSettings, settings_text, toggle_kind


class PreferencesTest(unittest.TestCase):
    def test_toggle_turns_a_kind_off_and_on(self):
        off = toggle_kind(DEFAULT_SETTINGS, "problem")
        self.assertEqual(off.kinds, frozenset({"request", "vacancy"}))
        self.assertEqual(toggle_kind(off, "problem").kinds, frozenset({"request", "vacancy", "problem"}))

    def test_text_warns_when_every_kind_is_off(self):
        self.assertIn("No lead alerts will come", settings_text(LeadSettings(frozenset(), "labels")))
        self.assertNotIn("No lead alerts will come", settings_text(DEFAULT_SETTINGS))

    def test_keyboard_marks_the_kinds_that_are_on(self):
        keyboard = lead_settings_keyboard(LeadSettings(frozenset({"request"}), "labels"))
        buttons = {button.callback_data: button.text for row in keyboard.inline_keyboard for button in row}
        self.assertTrue(buttons["lead_set:kind:request"].startswith("✅"))
        self.assertFalse(buttons["lead_set:kind:problem"].startswith("✅"))


if __name__ == "__main__":
    unittest.main()
