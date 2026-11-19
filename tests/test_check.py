import unittest

from core.analyzer.history_scanner import ScanResult
from core.leads.check import check_report, lead_matcher, parse_check_args
from tests.lead_corpus import WEB


class ParseCheckArgsTest(unittest.TestCase):
    def test_days_default_to_7(self):
        self.assertEqual(parse_check_args("@chat"), ("@chat", 7))

    def test_days_can_be_given(self):
        self.assertEqual(parse_check_args("https://t.me/chat 14"), ("https://t.me/chat", 14))

    def test_days_are_capped_at_30(self):
        self.assertEqual(parse_check_args("@chat 45"), ("@chat", 30))

    def test_no_chat_or_bad_days_is_none(self):
        for args in (None, "", "@chat zero", "@chat 0", "@chat 7 more"):
            with self.subTest(args=args):
                self.assertIsNone(parse_check_args(args))


class LeadMatcherTest(unittest.TestCase):
    def test_needs_a_kind_and_a_niche_word(self):
        match = lead_matcher([WEB])
        self.assertEqual(match("Нужен сайт для студии"), "request")
        self.assertIsNone(match("Нужен электрик"))
        self.assertIsNone(match("Обновил сайт"))


class CheckReportTest(unittest.TestCase):
    def test_report_counts_kinds_and_shows_at_most_5_links(self):
        found = [("request", f"https://t.me/chat/{n}") for n in range(6)] + [("problem", "https://t.me/chat/9")]
        text = check_report("@chat", 7, ScanResult(40, found))
        self.assertIn("Messages checked: 40", text)
        self.assertIn("Requests: 6", text)
        self.assertIn("Vacancies: 0", text)
        self.assertIn("Problems: 1", text)
        self.assertEqual(text.count("https://t.me/chat/"), 5)

    def test_report_without_leads_says_so(self):
        self.assertIn("No leads", check_report("@chat", 7, ScanResult(40, [])))

    def test_report_for_an_unreadable_chat(self):
        # The check also fails when Telegram asks to wait longer than a minute: the text must not blame the chat alone.
        report = check_report("@chat", 7, None)
        self.assertIn("Couldn't read", report)
        self.assertIn("wait", report)

    def test_report_for_an_empty_history(self):
        self.assertIn("hides its history", check_report("@chat", 7, ScanResult(0, [])))

    def test_report_escapes_the_chat(self):
        self.assertIn("&lt;b&gt;", check_report("<b>", 7, None))


if __name__ == "__main__":
    unittest.main()
