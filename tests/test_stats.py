import unittest

from core.database.queries import add_channel, lead_stats, save_lead
from core.leads.stats import stats_lines
from tests.db import DbTestCase

DAY = 24 * 3600
NOW = 1_700_000_000


class LeadStatsQueryTest(DbTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await add_channel(-1001, "webchat", "Web chat")
        await add_channel(-1002, "seochat", "SEO chat")

    async def lead(self, channel_db_id, verdict=None, owner_id=10, created_at=NOW - DAY):
        await save_lead(owner_id, channel_db_id, 5, "https://t.me/webchat/5", "@ann", "request", "Нужен сайт", "h",
                        created_at, verdict=verdict)

    async def test_stats_count_each_verdict_per_chat(self):
        for verdict in ("reply", "not_lead", None, None, "ai_dropped"):
            await self.lead(1, verdict)
        await self.lead(2)
        self.assertEqual(await lead_stats(10, since=NOW - 30 * DAY),
                         [("Web chat", 4, 1, 1, 2, 1), ("SEO chat", 1, 0, 0, 1, 0)])

    async def test_stats_skip_other_owners_and_old_leads(self):
        await self.lead(1, owner_id=20)
        await self.lead(1, created_at=NOW - 31 * DAY)
        self.assertEqual(await lead_stats(10, since=NOW - 30 * DAY), [])


class StatsLinesTest(unittest.TestCase):
    def test_line_shows_dropped_by_ai_only_when_there_are_some(self):
        self.assertEqual(stats_lines([("Web", 12, 3, 5, 4, 0)]),
                         ["▪️ <b>Web</b>: 12 alerts · 3 I'll reply · 5 not a lead · 4 unmarked"])
        self.assertEqual(stats_lines([("Web", 1, 0, 1, 0, 7)]),
                         ["▪️ <b>Web</b>: 1 alert · 0 I'll reply · 1 not a lead · 0 unmarked · 7 dropped by AI"])

    def test_chat_titles_are_escaped(self):
        self.assertIn("&lt;b&gt;", stats_lines([("<b>", 1, 0, 0, 1, 0)])[0])


if __name__ == "__main__":
    unittest.main()
