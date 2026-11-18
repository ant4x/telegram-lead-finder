import asyncio
import unittest

from telethon.errors import ChannelsTooMuchError, FloodWaitError

from core.monitoring.joiner import JOIN_PAUSE_SECONDS, join_next


class Fakes:
    """Stands in for Telegram: join returns the given result or raises it; notes and pauses are recorded."""

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
    async def test_pauses_after_joining(self):
        fakes = Fakes(True)
        self.assertTrue(await fakes.step())
        self.assertEqual((fakes.pauses, fakes.notes), ([JOIN_PAUSE_SECONDS], []))

    async def test_does_not_pause_when_already_a_member(self):
        fakes = Fakes(False)
        self.assertTrue(await fakes.step())
        self.assertEqual(fakes.pauses, [])

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


if __name__ == "__main__":
    unittest.main()
