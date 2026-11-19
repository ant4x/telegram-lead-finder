import unittest

from core.database.queries import add_niche, add_niche_word, delete_niche, get_niches
from core.leads.rules import Niche
from tests.db import DbTestCase


class NicheQueriesTest(DbTestCase):
    async def test_adding_a_niche_twice_returns_the_same_niche(self):
        first = await add_niche(10, "Websites")
        self.assertEqual(await add_niche(10, "Websites"), first)
        self.assertEqual(len(await get_niches(10)), 1)

    async def test_words_come_back_with_their_niche(self):
        niche_id = await add_niche(10, "Websites")
        self.assertEqual(await add_niche_word(niche_id, "SEO"), "added")
        await add_niche_word(niche_id, "сайт*")
        self.assertEqual(await add_niche_word(niche_id, "seo"), "exists")
        self.assertEqual(await get_niches(10), [Niche(niche_id, 10, "Websites", ("seo", "сайт*"))])

    async def test_a_niche_without_words_comes_back_empty(self):
        niche_id = await add_niche(10, "Repair")
        self.assertEqual(await get_niches(10), [Niche(niche_id, 10, "Repair", ())])

    async def test_owners_see_only_their_niches(self):
        await add_niche(10, "Websites")
        await add_niche(20, "Repair")
        self.assertEqual([niche.name for niche in await get_niches(10)], ["Websites"])
        self.assertEqual([niche.name for niche in await get_niches()], ["Repair", "Websites"])

    async def test_another_owner_cannot_delete_a_niche(self):
        niche_id = await add_niche(10, "Websites")
        self.assertFalse(await delete_niche(niche_id, owner_id=20))
        self.assertEqual(len(await get_niches(10)), 1)
        self.assertTrue(await delete_niche(niche_id, owner_id=10))
        self.assertEqual(await get_niches(10), [])


if __name__ == "__main__":
    unittest.main()
