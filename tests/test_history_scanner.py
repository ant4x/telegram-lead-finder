import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from telethon.tl.types import Channel, ChatPhotoEmpty, User

from core.analyzer import history_scanner
from core.analyzer.history_scanner import ScanResult, scan_chat, try_start_scan

NOW = datetime(2026, 11, 19, tzinfo=timezone.utc)
WEB_CHAT = Channel(id=1001, title="Web chat", photo=ChatPhotoEmpty(), date=None, username="webchat", megagroup=True)


class FakeClient:
    """Stands in for Telethon: one chat with the given messages, newest first."""

    def __init__(self, entity, messages):
        self.entity = entity
        self.messages = messages
        self.read = False

    async def get_entity(self, channel):
        return self.entity

    async def iter_messages(self, entity, limit=None):
        self.read = True
        for message in self.messages:
            yield message


def message(message_id, days_ago, text):
    return SimpleNamespace(id=message_id, date=NOW - timedelta(days=days_ago), raw_text=text)


def needs(text):
    return "request" if "Нужен" in text else None


class ScanChatTest(unittest.IsolatedAsyncioTestCase):
    async def test_stops_at_the_start_date_and_labels_matches(self):
        client = FakeClient(WEB_CHAT, [message(3, 0, "Нужен сайт"), message(2, 1, "Привет"),
                                       message(1, 10, "Нужен лендинг")])
        result = await scan_chat(client, "@webchat", needs, NOW - timedelta(days=7))
        self.assertEqual(result, ScanResult(2, [("request", "https://t.me/webchat/3")]))

    async def test_a_private_chat_with_a_person_is_not_read(self):
        person = User(id=7, first_name="Ann", username="ann")
        client = FakeClient(person, [message(1, 0, "Нужен сайт")])
        with self.assertLogs(level="WARNING"):
            self.assertIsNone(await scan_chat(client, "@ann", needs, NOW - timedelta(days=7)))
        self.assertFalse(client.read)


class TryStartScanTest(unittest.IsolatedAsyncioTestCase):
    async def test_try_start_scan_refuses_a_second_scan(self):
        gate = asyncio.Event()
        started = []

        async def scan():
            started.append(1)
            await gate.wait()

        self.assertTrue(try_start_scan(scan))
        self.assertFalse(try_start_scan(scan))
        gate.set()
        await history_scanner.scan_task
        self.assertEqual(started, [1])
        self.assertTrue(try_start_scan(scan))
        await history_scanner.scan_task


if __name__ == "__main__":
    unittest.main()
