import unittest
from types import SimpleNamespace

from core.leads.alert import Author, alert_text, author_of

LINK = "https://t.me/webchat/5"


class AlertTextTest(unittest.TestCase):
    def test_escapes_strangers_html(self):
        text = alert_text("request", ["Web"], "<b>Chat & Co</b>", Author("<Ann>", None), "a < b", LINK)
        self.assertIn("&lt;b&gt;Chat &amp; Co&lt;/b&gt;", text)
        self.assertIn("&lt;Ann&gt;", text)
        self.assertNotIn("<Ann>", text)
        self.assertIn("a &lt; b", text)

    def test_quote_is_cut_at_300(self):
        text = alert_text("request", ["Web"], "Chat", Author("Ann", None), "x" * 299 + "yz" + "w" * 99, LINK)
        self.assertIn("x" * 299 + "y...", text)
        self.assertNotIn("yz", text)

    def test_message_the_author_only_with_a_username(self):
        with_username = alert_text("request", ["Web"], "Chat", Author("@ann", "https://t.me/ann"), "hi", LINK)
        self.assertIn("<a href='https://t.me/ann'>Message the author</a>", with_username)
        without = alert_text("request", ["Web"], "Chat", Author("Ann Lee", None), "hi", LINK)
        self.assertNotIn("Message the author", without)
        self.assertIn(f"<a href='{LINK}'>Open the message</a>", without)

    def test_names_every_niche_and_the_kind(self):
        text = alert_text("problem", ["Web", "Repair"], "Chat", Author("Ann", None), "hi", LINK)
        self.assertIn("Web, Repair · Problem", text)


class AuthorOfTest(unittest.TestCase):
    def test_author_of_a_channel_post_is_the_channel(self):
        self.assertEqual(author_of(None, "Orders"), Author("Orders", None))
        self.assertEqual(author_of(SimpleNamespace(title="Orders board", username="orders"), "Orders"),
                         Author("Orders board", None))

    def test_a_user_with_a_username_can_be_messaged(self):
        ann = SimpleNamespace(username="ann", first_name="Ann", last_name=None)
        self.assertEqual(author_of(ann, "Chat"), Author("@ann", "https://t.me/ann"))

    def test_a_user_without_a_username_has_a_name_only(self):
        ann = SimpleNamespace(username=None, first_name="Ann", last_name="Lee")
        self.assertEqual(author_of(ann, "Chat"), Author("Ann Lee", None))


if __name__ == "__main__":
    unittest.main()
