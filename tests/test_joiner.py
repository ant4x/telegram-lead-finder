import asyncio
import unittest

from telethon.errors import ChannelsTooMuchError, FloodWaitError

from core.monitoring import joiner
from core.monitoring.joiner import JOIN_PAUSE_SECONDS, join_next


class Fakes:
    """Stands in for Telegram: join returns the given title (None: already a member) or raises; notes and pauses are recorded."""

    def __init__(self, result):
        self.result = result
        self.notes = []
        self.pauses = []
        self.pending = asyncio.Queue()

    async def join(self, channel):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    async def notify(self, text):
        self.notes.append(text)

    async def sleep(self, seconds):
        self.pauses.append(seconds)

    async def step(self, channel="@news"):
        return await join_next(channel, self.pending, self.join, self.notify, self.sleep)


class JoinNextTest(unittest.IsolatedAsyncioTestCase):
    async def test_tells_the_admins_and_pauses_after_joining(self):
        fakes = Fakes("Daily News")
        self.assertTrue(await fakes.step())
        self.assertEqual(fakes.pauses, [JOIN_PAUSE_SECONDS])
        self.assertEqual(len(fakes.notes), 1)
        self.assertIn("joined Daily News", fakes.notes[0])

    async def test_stays_quiet_when_already_a_member(self):
        fakes = Fakes(None)
        self.assertTrue(await fakes.step())
        self.assertEqual((fakes.pauses, fakes.notes), ([], []))

    async def test_waits_out_a_flood_wait_and_retries_the_channel(self):
        fakes = Fakes(FloodWaitError(request=None, capture=120))
        self.assertTrue(await fakes.step("@news"))
        self.assertEqual(fakes.pauses, [120])
        self.assertIn("2 min", fakes.notes[0])
        self.assertEqual(fakes.pending.get_nowait(), "@news")

    async def test_stops_at_the_channel_limit(self):
        fakes = Fakes(ChannelsTooMuchError(request=None))
        self.assertFalse(await fakes.step())
        self.assertIn("too many channels", fakes.notes[0])
        self.assertEqual(fakes.pauses, [])
        self.assertTrue(fakes.pending.empty())

    async def test_skips_a_channel_that_fails_otherwise(self):
        fakes = Fakes(ValueError("no such channel"))
        with self.assertLogs(level="ERROR"):
            self.assertTrue(await fakes.step())
        self.assertEqual((fakes.pauses, fakes.notes), ([], []))
        self.assertTrue(fakes.pending.empty())


class ApprovalTest(unittest.TestCase):
    """The account joins only channels an admin approved: approval moves them to the join queue."""

    def setUp(self):
        joiner.awaiting.clear()
        while not joiner.queue.empty():
            joiner.queue.get_nowait()

    def test_approval_queues_every_waiting_channel_in_order(self):
        joiner.awaiting.extend(["@first", "@second"])
        self.assertEqual(joiner.approve_awaiting(), 2)
        self.assertEqual([joiner.queue.get_nowait(), joiner.queue.get_nowait()], ["@first", "@second"])
        self.assertEqual(joiner.awaiting, [])

    def test_nothing_is_queued_before_approval(self):
        joiner.awaiting.append("@first")
        self.assertTrue(joiner.queue.empty())


if __name__ == "__main__":
    unittest.main()
