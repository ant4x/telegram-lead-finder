import asyncio
import unittest
from types import SimpleNamespace

from telethon.errors import ChannelsTooMuchError, FloodWaitError, InviteRequestSentError

from core.monitoring import joiner
from core.monitoring.joiner import JOIN_PAUSE_SECONDS, join_next


class Fakes:
    """Stands in for Telegram: join returns the given chat (None: already a member) or raises; notes and pauses are recorded."""

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


def joined(title, group=False):
    """The chat the account has just joined, as Telethon describes it."""
    return SimpleNamespace(title=title, megagroup=group)


class JoinNextTest(unittest.IsolatedAsyncioTestCase):
    async def test_tells_the_admins_and_pauses_after_joining(self):
        fakes = Fakes(joined("Daily News"))
        self.assertTrue(await fakes.step())
        self.assertEqual(fakes.pauses, [JOIN_PAUSE_SECONDS])
        self.assertEqual(len(fakes.notes), 1)
        self.assertIn("joined Daily News", fakes.notes[0])

    async def test_joining_a_group_warns_about_the_bot_check(self):
        fakes = Fakes(joined("Web chat", group=True))
        await fakes.step()
        self.assertIn("joined Web chat", fakes.notes[0])
        self.assertIn("not a bot", fakes.notes[0])

    async def test_joining_a_channel_has_no_such_warning(self):
        fakes = Fakes(joined("Daily News"))
        await fakes.step()
        self.assertNotIn("not a bot", fakes.notes[0])

    async def test_a_join_request_is_reported_and_paced(self):
        fakes = Fakes(InviteRequestSentError(request=None))
        self.assertTrue(await fakes.step("@club"))
        self.assertIn("@club", fakes.notes[0])
        self.assertIn("by request", fakes.notes[0])
        self.assertEqual(fakes.pauses, [JOIN_PAUSE_SECONDS])
        self.assertTrue(fakes.pending.empty())

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

    def test_one_channel_reads_in_the_singular(self):
        text = joiner.approval_request(["Daily News"])
        self.assertIn("isn't in 1 channel on the list", text)
        self.assertIn("Join it?", text)


class Channel:
    """A channel as Telegram returns it: left is True when the reading account is not a member."""

    def __init__(self, title, left):
        self.title = title
        self.left = left


class StartupCheckTest(unittest.IsolatedAsyncioTestCase):
    """At startup the admins hear that the list is empty, or get asked about channels the account is not in."""

    def setUp(self):
        joiner.awaiting.clear()

    async def check(self, channels: dict) -> list:
        notes = []

        async def get_entity(channel):
            if isinstance(channels[channel], Exception):
                raise channels[channel]
            return channels[channel]

        async def notify(text, keyboard=None):
            notes.append((text, keyboard))

        await joiner.check_channels(list(channels), get_entity, notify)
        return notes

    async def test_an_empty_list_asks_the_admins_to_add_channels(self):
        self.assertEqual(await self.check({}), [(joiner.NO_CHANNELS, None)])
        self.assertIn("/add_channel", joiner.NO_CHANNELS)

    async def test_asks_only_about_channels_the_account_is_not_in(self):
        notes = await self.check({"@in": Channel("Inside", False), "@out": Channel("Outside", True)})
        self.assertEqual(joiner.awaiting, ["@out"])
        self.assertEqual(len(notes), 1)
        text, keyboard = notes[0]
        self.assertIn("Outside", text)
        self.assertNotIn("Inside", text)
        self.assertIsNotNone(keyboard)

    async def test_a_chat_that_cannot_be_opened_does_not_stop_the_check(self):
        # A chat on the list may be deleted or turn private; the error used to stop the joiner for the whole run.
        notes = await self.check({"@gone": ValueError("No user has gone as username"),
                                  "@out": Channel("Outside", True)})
        self.assertEqual(joiner.awaiting, ["@out"])
        self.assertEqual(len(notes), 1)
        self.assertIn("Outside", notes[0][0])

    async def test_stays_quiet_when_the_account_is_in_every_channel(self):
        self.assertEqual(await self.check({"@in": Channel("Inside", False)}), [])
        self.assertEqual(joiner.awaiting, [])


if __name__ == "__main__":
    unittest.main()
