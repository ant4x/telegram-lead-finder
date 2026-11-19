import unittest

from core.text import plural, post_link, quote, split_message


class PluralTest(unittest.TestCase):
    def test_one_is_singular(self):
        self.assertEqual(plural(1, "channel"), "1 channel")

    def test_other_numbers_are_plural(self):
        self.assertEqual([plural(0, "channel"), plural(2, "channel")], ["0 channels", "2 channels"])


class QuoteTest(unittest.TestCase):
    def test_escapes_html(self):
        self.assertEqual(quote("price < $1 & up"), "price &lt; $1 &amp; up")

    def test_short_text_has_no_ellipsis(self):
        self.assertEqual(quote("short post"), "short post")

    def test_long_text_is_cut_before_escaping(self):
        text = "a" * 199 + "&" + "b" * 10
        self.assertEqual(quote(text), "a" * 199 + "&amp;...")


class SplitMessageTest(unittest.TestCase):
    def test_short_list_is_one_message(self):
        self.assertEqual(split_message("Links:", ["one", "two"]), ["Links:\none\ntwo"])

    def test_long_list_fits_the_limit_and_keeps_every_line(self):
        lines = [f"https://t.me/channel/{number}" for number in range(1000)]
        messages = split_message("Links:", lines, limit=100)
        self.assertTrue(all(len(message) <= 100 for message in messages))
        self.assertTrue(messages[0].startswith("Links:\n"))
        self.assertEqual("\n".join(messages).split("\n")[1:], lines)


class PostLinkTest(unittest.TestCase):
    def test_public_channel_link_uses_the_username(self):
        self.assertEqual(post_link("news", 1234567890, 7), "https://t.me/news/7")

    def test_private_channel_link_uses_the_id(self):
        self.assertEqual(post_link(None, 1234567890, 7), "https://t.me/c/1234567890/7")


if __name__ == "__main__":
    unittest.main()
