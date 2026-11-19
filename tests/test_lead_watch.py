import unittest
from types import SimpleNamespace

from core.database.queries import add_channel, add_niche, add_niche_word
from core.leads.watch import process_lead_message
from tests.db import DbTestCase

NOW = 1_700_000_000
CHAT = SimpleNamespace(title="Web chat", username="webchat", id=1001)
ANN = SimpleNamespace(bot=False, username="ann", first_name="Ann", last_name=None)


def message(text, chat_id=-1001, out=False, sender=ANN):
    """A new message as Telethon hands it over, with only the parts the lead finder reads."""
    async def get_sender():
        return sender

    async def get_chat():
        return CHAT

    return SimpleNamespace(message=SimpleNamespace(raw_text=text, id=5), out=out, chat_id=chat_id,
                           get_sender=get_sender, get_chat=get_chat)


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text, kwargs))


class LeadWatchTest(DbTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await add_channel(-1001, "webchat", "Web chat")
        await add_niche_word(await add_niche(10, "Websites"), "сайт*")
        await add_niche_word(await add_niche(20, "Repair"), "ремонт*")
        self.bot = FakeBot()

    async def handle(self, event, at=NOW):
        await process_lead_message(event, self.bot, now=lambda: at)

    async def test_the_niche_owner_gets_the_alert_and_no_one_else(self):
        await self.handle(message("Нужен сайт для студии йоги"))
        self.assertEqual([chat_id for chat_id, _, _ in self.bot.sent], [10])
        _, text, kwargs = self.bot.sent[0]
        self.assertIn("Websites · Request", text)
        self.assertIn("https://t.me/webchat/5", text)
        self.assertIsNotNone(kwargs["reply_markup"])

    async def test_each_owner_gets_one_alert_for_their_niches(self):
        await self.handle(message("Нужен сайт и ремонт офиса"))
        self.assertEqual(sorted(chat_id for chat_id, _, _ in self.bot.sent), [10, 20])

    async def test_one_alert_for_the_same_text_within_a_day(self):
        await self.handle(message("Нужен сайт для студии"), at=NOW)
        await self.handle(message("нужен сайт для студии  https://t.me/x/1"), at=NOW + 3600)
        self.assertEqual(len(self.bot.sent), 1)
        await self.handle(message("Нужен сайт для студии"), at=NOW + 25 * 3600)
        self.assertEqual(len(self.bot.sent), 2)

    async def test_own_messages_and_bots_are_skipped(self):
        await self.handle(message("Нужен сайт", out=True))
        await self.handle(message("Нужен сайт", sender=SimpleNamespace(bot=True, username="helper_bot")))
        self.assertEqual(self.bot.sent, [])

    async def test_a_chat_off_the_list_is_skipped(self):
        await self.handle(message("Нужен сайт", chat_id=-1009))
        self.assertEqual(self.bot.sent, [])

    async def test_no_niche_word_no_alert(self):
        await self.handle(message("Нужен электрик"))
        self.assertEqual(self.bot.sent, [])


if __name__ == "__main__":
    unittest.main()
