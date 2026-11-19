import unittest

from core.text import mentions


class MentionsTest(unittest.TestCase):
    def test_finds_the_word_in_any_case(self):
        self.assertTrue(mentions("TON is up today", "ton"))

    def test_skips_the_word_inside_another_word(self):
        self.assertFalse(mentions("press the button in Boston", "ton"))

    def test_finds_a_phrase(self):
        self.assertTrue(mentions("New Acme Wallet is out", "acme wallet"))

    def test_a_phrase_matches_across_any_spaces(self):
        self.assertTrue(mentions("Кто\nсделает лендинг?", "кто сделает"))
        self.assertTrue(mentions("кто  возьмётся за сайт", "кто возьмётся"))

    def test_finds_the_word_next_to_punctuation(self):
        self.assertTrue(mentions("#ton, $ton!", "ton"))

    def test_word_boundaries_work_for_cyrillic(self):
        self.assertTrue(mentions("Тон растёт", "тон"))
        self.assertFalse(mentions("тонна угля", "тон"))

    def test_other_forms_of_a_word_are_other_words(self):
        self.assertFalse(mentions("Ищу разработчика сайта", "сайт"))

    def test_star_finds_every_word_that_starts_with_the_keyword(self):
        self.assertTrue(mentions("Ищу разработчика сайта", "сайт*"))
        self.assertTrue(mentions("Нужен сайт для салона", "сайт*"))

    def test_star_still_needs_the_start_of_a_word(self):
        self.assertFalse(mentions("посайтовая оплата", "сайт*"))

    def test_keyword_with_symbols_is_matched_literally(self):
        self.assertTrue(mentions("I like C++ a lot", "c++"))
        self.assertFalse(mentions("I like Cpp a lot", "c++"))


if __name__ == "__main__":
    unittest.main()
