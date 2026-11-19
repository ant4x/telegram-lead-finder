import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

from core.database.queries import add_channel, add_niche, add_niche_word, execute_query, save_lead_settings
from core.leads.ai import AiConfig, AiVerdict
from core.leads.preferences import LeadSettings
from core.leads.rules import KINDS
from core.leads import watch
from core.leads.watch import process_lead_message
from core.limits import DailyLimit
from tests.db import DbTestCase

NOW = 1_700_000_000
NO_AI = AiConfig("", "", "https://ai.example/api/v1")
AI = AiConfig("sk-test", "test/model", "https://ai.example/api/v1")
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
        # The bot runs one event loop; each test has its own, and on Python 3.10 a lock stays with its first loop.
        patcher = mock.patch.object(watch, "dedup_lock", asyncio.Lock())
        patcher.start()
        self.addCleanup(patcher.stop)
        await add_channel(-1001, "webchat", "Web chat")
        await add_niche_word(await add_niche(10, "Websites"), "сайт*")
        await add_niche_word(await add_niche(20, "Repair"), "ремонт*")
        self.bot = FakeBot()
        self.ai = NO_AI
        self.verdict = None
        self.checks = []
        self.limit = DailyLimit(300)

    async def check(self, config, text, niches, kind):
        """Stands in for the AI: records the call, lets other tasks run as a real request would, gives the verdict."""
        self.checks.append(text)
        await asyncio.sleep(0)
        return self.verdict

    async def handle(self, event, at=NOW):
        await process_lead_message(event, self.bot, ai=self.ai, check=self.check, limit=self.limit, now=lambda: at)

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

    async def test_a_kind_turned_off_sends_nothing(self):
        await save_lead_settings(10, LeadSettings(frozenset({"request", "vacancy"}), "labels"))
        await self.handle(message("Сайт перестал открываться, помогите"))
        self.assertEqual(self.bot.sent, [])
        await self.handle(message("Нужен сайт для студии"))
        self.assertEqual(len(self.bot.sent), 1)

    async def test_the_same_text_arriving_at_once_alerts_once(self):
        await add_channel(-1002, "seochat", "SEO chat")
        await asyncio.gather(self.handle(message("Нужен сайт для студии")),
                             self.handle(message("Нужен сайт для студии", chat_id=-1002)))
        self.assertEqual(len(self.bot.sent), 1)
        self.assertEqual(await execute_query("SELECT COUNT(*) FROM leads", fetchone=True), (1,))


class AiCheckTest(LeadWatchTest):
    """The same listener with the AI check: the owner's mode decides what the AI's answer changes."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.ai = AI

    async def use_mode(self, mode):
        await save_lead_settings(10, LeadSettings(frozenset(KINDS), mode))

    async def test_labels_mode_adds_the_ai_line(self):
        self.verdict = AiVerdict(True, "request", "client", "wants a studio site")
        await self.handle(message("Нужен сайт для студии"))
        self.assertIn("🤖 AI: client · wants a studio site", self.bot.sent[0][1])

    async def test_filter_mode_keeps_rejected_leads_out_of_alerts(self):
        await self.use_mode("filter")
        self.verdict = AiVerdict(False, None, "peer", "talks about his own site")
        await self.handle(message("Нужен совет по сайту, коллеги"))
        self.assertEqual(self.bot.sent, [])
        self.assertEqual(await execute_query("SELECT verdict, ai_author FROM leads", fetchall=True),
                         [("ai_dropped", "peer")])

    async def test_the_ai_kind_replaces_the_rules_kind(self):
        self.verdict = AiVerdict(True, "vacancy", "client", "hires a developer")
        await self.handle(message("Нужен разработчик сайтов в штат"))
        self.assertIn("Websites · Vacancy", self.bot.sent[0][1])

    async def test_failed_ai_check_still_sends_the_lead(self):
        await self.use_mode("filter")
        self.verdict = None
        await self.handle(message("Нужен сайт для студии"))
        self.assertIn("AI check failed", self.bot.sent[0][1])

    async def test_off_mode_and_no_key_skip_the_ai(self):
        await self.use_mode("off")
        await self.handle(message("Нужен сайт для студии"))
        self.ai = NO_AI
        await self.use_mode("labels")
        await self.handle(message("Нужен сайт для кафе"))
        self.assertEqual(self.checks, [])
        self.assertEqual(len(self.bot.sent), 2)

    async def test_ai_limit_warns_once_and_falls_back_to_rules(self):
        self.limit = DailyLimit(2)
        self.verdict = AiVerdict(True, "request", "client", "wants a site")
        for text in ("Нужен сайт", "Нужен сайт для студии", "Нужен сайт для кафе"):
            await self.handle(message(text))
        self.assertEqual(len(self.checks), 2)
        texts = [text for _, text, _ in self.bot.sent]
        self.assertEqual(sum("AI checks are used up" in text for text in texts), 1)
        self.assertNotIn("🤖 AI", texts[-1])

    async def test_leads_at_once_do_not_overshoot_the_ai_cap(self):
        self.limit = DailyLimit(1)
        self.verdict = AiVerdict(True, "request", "client", "wants a site")
        await asyncio.gather(*(self.handle(message(text)) for text in
                               ("Нужен сайт", "Нужен сайт для студии", "Нужен сайт для кафе")))
        self.assertEqual(len(self.checks), 1)


if __name__ == "__main__":
    unittest.main()
