import unittest

from core.database import queries
from core.database.queries import (add_channel, add_niche, add_niche_word, delete_niche, execute_query,
                                   get_lead_settings, get_niches, purge_old_leads, save_lead, save_lead_settings,
                                   seen_recently, set_lead_verdict)
from core.leads.preferences import DEFAULT_SETTINGS, LeadSettings
from core.leads.rules import Niche
from tests.db import DbTestCase


class NicheQueriesTest(DbTestCase):
    async def test_adding_a_niche_twice_returns_the_same_niche(self):
        first = await add_niche(10, "Websites")
        self.assertEqual(await add_niche(10, "Websites"), first)
        self.assertEqual(len(await get_niches(10)), 1)

    async def test_a_word_for_a_niche_deleted_meanwhile_says_so(self):
        # The niche can be removed with /del_niche's old buttons while the bot waits for its next word.
        niche_id = await add_niche(10, "Websites")
        await delete_niche(niche_id, 10)
        self.assertEqual(await add_niche_word(niche_id, "SEO"), "gone")

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


DAY = 24 * 3600
NOW = 1_700_000_000


class LeadQueriesTest(DbTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await add_channel(-1001, "webchat", "Web chat")

    async def lead(self, created_at=NOW, owner_id=10, text_hash="h1"):
        return await save_lead(owner_id, 1, 5, "https://t.me/webchat/5", "@ann", "request", "Нужен сайт",
                               text_hash, created_at)

    async def test_seen_recently_counts_only_the_window(self):
        await self.lead(created_at=NOW)
        self.assertTrue(await seen_recently(10, "h1", since=NOW - DAY))
        self.assertFalse(await seen_recently(10, "h1", since=NOW + 1))
        self.assertFalse(await seen_recently(20, "h1", since=NOW - DAY))
        self.assertFalse(await seen_recently(10, "h2", since=NOW - DAY))

    async def test_another_owner_cannot_mark_a_lead(self):
        lead_id = await self.lead()
        self.assertFalse(await set_lead_verdict(lead_id, owner_id=20, verdict="reply"))
        self.assertEqual(await execute_query("SELECT verdict FROM leads", fetchone=True), (None,))
        self.assertTrue(await set_lead_verdict(lead_id, owner_id=10, verdict="reply"))
        self.assertEqual(await execute_query("SELECT verdict FROM leads", fetchone=True), ("reply",))

    async def test_purge_keeps_counts_and_erases_text(self):
        old = await self.lead(created_at=NOW - 31 * DAY)
        await set_lead_verdict(old, 10, "not_lead")
        new = await self.lead(created_at=NOW - DAY)
        self.assertEqual(await purge_old_leads(before=NOW - 30 * DAY), 1)
        query = "SELECT text, author, link, message_id, text_hash, summary, kind, verdict FROM leads WHERE id = ?"
        self.assertEqual(await execute_query(query, (old,), fetchone=True),
                         (None, None, None, None, None, None, "request", "not_lead"))
        self.assertEqual(await execute_query(query, (new,), fetchone=True),
                         ("Нужен сайт", "@ann", "https://t.me/webchat/5", 5, "h1", None, "request", None))

    async def test_purged_text_is_gone_from_the_database_file(self):
        # Without secure_delete SQLite only marks the old bytes free, and the author and the link stay readable.
        await save_lead(10, 1, 5, "https://t.me/secretchat/5", "@secret_author", "request", "Нужен сайт", "h1",
                        NOW - 31 * DAY)
        await purge_old_leads(before=NOW - 30 * DAY)
        with open(queries.DB_NAME, "rb") as file:
            data = file.read()
        self.assertFalse(b"secret_author" in data, "the author is still in the file")
        self.assertFalse(b"secretchat" in data, "the link is still in the file")


class LeadSettingsQueriesTest(DbTestCase):
    async def test_settings_default_until_saved(self):
        self.assertEqual(await get_lead_settings(10), DEFAULT_SETTINGS)

    async def test_saved_settings_come_back(self):
        await save_lead_settings(10, LeadSettings(frozenset({"request"}), "filter"))
        self.assertEqual(await get_lead_settings(10), LeadSettings(frozenset({"request"}), "filter"))
        await save_lead_settings(10, LeadSettings(frozenset(), "off"))
        self.assertEqual(await get_lead_settings(10), LeadSettings(frozenset(), "off"))
        self.assertEqual(await get_lead_settings(20), DEFAULT_SETTINGS)


if __name__ == "__main__":
    unittest.main()
