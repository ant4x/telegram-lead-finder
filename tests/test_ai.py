import asyncio
import json
import unittest
from unittest import mock

import aiohttp

from core.leads.ai import (INPUT_LIMIT, AiConfig, AiVerdict, ai_line, check_lead, dropped_by_ai, parse_verdict)
from tests.lead_corpus import WEB

CONFIG = AiConfig("sk-test-secret", "test/model", "https://ai.example/api/v1")
SECRET_TEXT = "Нужен сайт, мой телефон +995 555 12 34"


def answer(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


GOOD = json.dumps({"lead": True, "kind": "request", "author": "client", "summary": "wants a studio site"})


class FakePost:
    """Stands in for the HTTP call: records what was sent and returns or raises what it was given."""

    def __init__(self, result):
        self.result = result
        self.calls = []

    async def __call__(self, url, headers, payload, timeout):
        self.calls.append((url, headers, payload, timeout))
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class CheckLeadTest(unittest.IsolatedAsyncioTestCase):
    async def test_a_good_answer_becomes_a_verdict(self):
        verdict = await check_lead(CONFIG, "Нужен сайт", [WEB], "request", post=FakePost(answer(GOOD)))
        self.assertEqual(verdict, AiVerdict(True, "request", "client", "wants a studio site"))

    async def test_sends_the_model_key_and_cut_text(self):
        post = FakePost(answer(GOOD))
        await check_lead(CONFIG, "Нужен сайт " + "x" * 3000, [WEB], "request", post=post)
        url, headers, payload, timeout = post.calls[0]
        self.assertEqual(url, "https://ai.example/api/v1/chat/completions")
        self.assertEqual(headers["Authorization"], "Bearer sk-test-secret")
        self.assertEqual(payload["model"], "test/model")
        self.assertEqual(timeout, 20)
        sent = payload["messages"][-1]["content"]
        self.assertIn("Нужен сайт", sent)
        self.assertNotIn("x" * (INPUT_LIMIT + 1), sent)
        self.assertIn("Websites and SEO", sent)

    async def test_an_empty_base_url_means_openrouter(self):
        post = FakePost(answer(GOOD))
        await check_lead(AiConfig("sk-test-secret", "test/model", ""), "Нужен сайт", [WEB], "request", post=post)
        self.assertEqual(post.calls[0][0], "https://openrouter.ai/api/v1/chat/completions")

    async def test_timeout_gives_none_and_logs_no_text(self):
        with self.assertLogs(level="WARNING") as logs:
            self.assertIsNone(await check_lead(CONFIG, SECRET_TEXT, [WEB], "request",
                                               post=FakePost(asyncio.TimeoutError())))
        logged = "\n".join(logs.output)
        self.assertNotIn(SECRET_TEXT, logged)
        self.assertNotIn("sk-test-secret", logged)

    async def test_an_http_error_logs_its_status(self):
        # 401 means a wrong key, 400 or 404 often a wrong model name: the owner needs the code to tell them apart.
        error = aiohttp.ClientResponseError(mock.Mock(real_url="https://ai.example"), (), status=401,
                                            message="Unauthorized")
        with self.assertLogs(level="WARNING") as logs:
            self.assertIsNone(await check_lead(CONFIG, SECRET_TEXT, [WEB], "request", post=FakePost(error)))
        logged = "\n".join(logs.output)
        self.assertIn("401", logged)
        self.assertNotIn("sk-test-secret", logged)

    async def test_an_answer_of_the_wrong_shape_gives_none(self):
        with self.assertLogs(level="WARNING"):
            self.assertIsNone(await check_lead(CONFIG, SECRET_TEXT, [WEB], "request", post=FakePost({"error": "x"})))


class ParseVerdictTest(unittest.TestCase):
    def test_parse_accepts_fenced_json(self):
        self.assertEqual(parse_verdict(f"```json\n{GOOD}\n```"), AiVerdict(True, "request", "client",
                                                                             "wants a studio site"))

    def test_parse_rejects_garbage_and_wrong_kind(self):
        for content in ("I think it is a lead", "[1, 2]", json.dumps({"lead": "yes", "kind": "request"}),
                        json.dumps({"lead": True, "kind": "order"})):
            with self.subTest(content=content):
                self.assertIsNone(parse_verdict(content))

    def test_not_a_lead_needs_no_kind(self):
        verdict = parse_verdict(json.dumps({"lead": False, "kind": None, "author": "peer", "summary": "chat"}))
        self.assertEqual(verdict, AiVerdict(False, None, "peer", "chat"))

    def test_unknown_author_becomes_unknown(self):
        verdict = parse_verdict(json.dumps({"lead": True, "kind": "problem", "author": "boss", "summary": "s"}))
        self.assertEqual(verdict.author, "unknown")

    def test_summary_is_cut_to_200(self):
        verdict = parse_verdict(json.dumps({"lead": True, "kind": "request", "author": "client", "summary": "s" * 500}))
        self.assertEqual(len(verdict.summary), 200)


class DroppedByAiTest(unittest.TestCase):
    ALL = frozenset({"request", "vacancy", "problem"})

    def test_filter_drops_only_what_ai_rejects(self):
        rejected = AiVerdict(False, None, "peer", "")
        accepted = AiVerdict(True, "request", "client", "")
        for mode in ("off", "labels"):
            self.assertFalse(dropped_by_ai(mode, rejected, self.ALL))
        self.assertTrue(dropped_by_ai("filter", rejected, self.ALL))
        self.assertFalse(dropped_by_ai("filter", accepted, self.ALL))
        self.assertTrue(dropped_by_ai("filter", accepted, frozenset({"problem"})))
        self.assertFalse(dropped_by_ai("filter", None, self.ALL))


class AiLineTest(unittest.TestCase):
    def test_line_names_the_author_and_the_need(self):
        self.assertEqual(ai_line(AiVerdict(True, "request", "client", "wants a <site>"), failed=False),
                         "🤖 AI: client · wants a &lt;site&gt;")

    def test_line_says_when_it_is_likely_not_a_lead(self):
        self.assertEqual(ai_line(AiVerdict(False, None, "peer", ""), failed=False),
                         "🤖 AI: likely not a lead · colleague")

    def test_failure_and_no_check(self):
        self.assertIn("AI check failed", ai_line(None, failed=True))
        self.assertIsNone(ai_line(None, failed=False))


if __name__ == "__main__":
    unittest.main()
