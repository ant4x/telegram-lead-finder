import unittest

from core.text import valid_keyword


class ValidKeywordTest(unittest.TestCase):
    def test_accepts_names_with_a_letter_or_digit(self):
        for keyword in ("acme", "c++", "сайт*", "web3"):
            self.assertTrue(valid_keyword(keyword), keyword)

    def test_rejects_names_that_would_match_every_post(self):
        for keyword in ("**", "*!", "..."):
            self.assertFalse(valid_keyword(keyword), keyword)

    def test_rejects_too_short_and_too_long_names(self):
        self.assertFalse(valid_keyword("a"))
        self.assertFalse(valid_keyword("a" * 100))


if __name__ == "__main__":
    unittest.main()
