import unittest

from core.keyboards.lead_settings_kb import lead_settings_keyboard
from core.leads.preferences import DEFAULT_SETTINGS, LeadSettings, settings_text, toggle_kind


def buttons(keyboard):
    return {button.callback_data: button.text for row in keyboard.inline_keyboard for button in row}


class PreferencesTest(unittest.TestCase):
    def test_toggle_turns_a_kind_off_and_on(self):
        off = toggle_kind(DEFAULT_SETTINGS, "problem")
        self.assertEqual(off.kinds, frozenset({"request", "vacancy"}))
        self.assertEqual(toggle_kind(off, "problem").kinds, frozenset({"request", "vacancy", "problem"}))

    def test_text_warns_when_every_kind_is_off(self):
        self.assertIn("No lead alerts will come", settings_text(LeadSettings(frozenset(), "labels"), False))
        self.assertNotIn("No lead alerts will come", settings_text(DEFAULT_SETTINGS, False))

    def test_keyboard_marks_the_kinds_that_are_on(self):
        shown = buttons(lead_settings_keyboard(LeadSettings(frozenset({"request"}), "labels"), False))
        self.assertTrue(shown["lead_set:kind:request"].startswith("✅"))
        self.assertFalse(shown["lead_set:kind:problem"].startswith("✅"))

    def test_ai_row_only_with_a_key(self):
        with_key = buttons(lead_settings_keyboard(LeadSettings(frozenset({"request"}), "filter"), True))
        self.assertTrue(with_key["lead_set:ai:filter"].startswith("✅"))
        self.assertFalse(with_key["lead_set:ai:labels"].startswith("✅"))
        without = buttons(lead_settings_keyboard(DEFAULT_SETTINGS, False))
        self.assertNotIn("lead_set:ai:filter", without)
        self.assertIn("AI_API_KEY", settings_text(DEFAULT_SETTINGS, False))
        self.assertNotIn("AI_API_KEY", settings_text(DEFAULT_SETTINGS, True))


if __name__ == "__main__":
    unittest.main()
