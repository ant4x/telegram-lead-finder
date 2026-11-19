import asyncio
import unittest

from core.database.queries import add_channel, execute_query, save_lead
from core.leads.retention import run_purge
from tests.db import DbTestCase

DAY = 24 * 3600
NOW = 1_700_000_000


class RunPurgeTest(DbTestCase):
    async def test_purges_at_startup_and_then_waits_a_day(self):
        await add_channel(-1001, "webchat", "Web chat")
        await save_lead(10, 1, 5, "https://t.me/webchat/5", "@ann", "request", "Нужен сайт", "h1", NOW - 31 * DAY)
        await save_lead(10, 1, 6, "https://t.me/webchat/6", "@bob", "request", "Нужен лендинг", "h2", NOW - 29 * DAY)
        pauses = []

        async def sleep(seconds):
            pauses.append(seconds)
            raise asyncio.CancelledError

        with self.assertRaises(asyncio.CancelledError):
            await run_purge(now=lambda: NOW, sleep=sleep)
        self.assertEqual(await execute_query("SELECT text FROM leads ORDER BY id", fetchall=True),
                         [(None,), ("Нужен лендинг",)])
        self.assertEqual(pauses, [DAY])


if __name__ == "__main__":
    unittest.main()
