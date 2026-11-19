import unittest

from core.commands import start_text
from core.modules import parse_modules


class ParseModulesTest(unittest.TestCase):
    def test_mentions_alone(self):
        self.assertEqual(parse_modules(["mentions"]), frozenset({"mentions"}))

    def test_both_with_spaces_and_case(self):
        self.assertEqual(parse_modules([" Leads", "mentions "]), frozenset({"mentions", "leads"}))

    def test_unknown_module_is_an_error(self):
        with self.assertRaises(ValueError):
            parse_modules(["mentions", "spam"])

    def test_no_module_is_an_error(self):
        with self.assertRaises(ValueError):
            parse_modules([])


class StartTextTest(unittest.TestCase):
    def test_start_lists_only_enabled_modules(self):
        mentions = start_text("Ann", frozenset({"mentions"}))
        self.assertIn("/analyze", mentions)
        self.assertIn("/add_channel", mentions)
        leads = start_text("Ann", frozenset({"leads"}))
        self.assertNotIn("/analyze", leads)
        self.assertNotIn("/add_project", leads)
        self.assertIn("/add_channel", leads)

    def test_start_escapes_the_name(self):
        self.assertIn("&lt;b&gt;", start_text("<b>", frozenset({"mentions"})))


if __name__ == "__main__":
    unittest.main()
