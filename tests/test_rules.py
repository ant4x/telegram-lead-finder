import unittest

from core.leads.rules import lead_kind, matching_niches, text_hash
from tests.lead_corpus import CORPUS, POWER, WEB


class CorpusTest(unittest.TestCase):
    def test_corpus(self):
        for text, expected in CORPUS:
            with self.subTest(text=text):
                found = matching_niches(text, [WEB, POWER])
                self.assertEqual(lead_kind(text) if found else None, expected)


class MatchingNichesTest(unittest.TestCase):
    def test_niche_words_pick_the_niche(self):
        self.assertEqual(matching_niches("Нужен электрик", [WEB, POWER]), [POWER])

    def test_a_message_can_match_several_niches(self):
        self.assertEqual(matching_niches("Нужен сайт для электрика", [WEB, POWER]), [WEB, POWER])


class TextHashTest(unittest.TestCase):
    def test_hash_ignores_case_and_spaces(self):
        self.assertEqual(text_hash("Нужен  сайт\nсрочно"), text_hash("нужен сайт срочно"))

    def test_hash_keeps_links(self):
        # Order feeds post the same short text with a link to each order, and people sign with their own contact.
        self.assertNotEqual(text_hash("Нужен сайт на Tilda https://kwork.ru/projects/111"),
                            text_hash("Нужен сайт на Tilda https://kwork.ru/projects/222"))
        self.assertNotEqual(text_hash("Нужен лендинг, пишите t.me/ivan"), text_hash("Нужен лендинг, пишите t.me/petr"))

    def test_hash_differs_for_other_text(self):
        self.assertNotEqual(text_hash("Нужен сайт"), text_hash("Нужен лендинг"))


if __name__ == "__main__":
    unittest.main()
