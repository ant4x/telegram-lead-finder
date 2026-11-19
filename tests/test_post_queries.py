import unittest
from datetime import datetime, timezone

from core.database.queries import add_channel, execute_query, log_mention, save_post
from tests.db import DbTestCase


class PostQueriesTest(DbTestCase):
    async def test_a_saved_post_gets_an_id_its_mentions_refer_to(self):
        await add_channel(-1001, "news", "News")
        await execute_query("INSERT INTO projects (name) VALUES ('acme')")
        first = await save_post(1, 7, "https://t.me/news/7", datetime(2026, 1, 1, tzinfo=timezone.utc), "acme is out")
        second = await save_post(1, 8, "https://t.me/news/8", datetime(2026, 1, 2, tzinfo=timezone.utc), "acme again")
        self.assertEqual((first, second), (1, 2))
        await log_mention(post_db_id=second, project_db_id=1)
        self.assertEqual(await execute_query("SELECT post_db_id FROM mentions", fetchall=True), [(2,)])


if __name__ == "__main__":
    unittest.main()
