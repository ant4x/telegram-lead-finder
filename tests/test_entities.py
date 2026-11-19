import unittest

from core.utils.entities import cached_entity, chat_ref


class FakeClient:
    """Records how a chat is looked up: the cached input entity first, then the full entity."""

    def __init__(self):
        self.calls = []

    async def get_input_entity(self, chat):
        self.calls.append(("input", chat))
        return f"input:{chat}"

    async def get_entity(self, chat):
        self.calls.append(("entity", chat))
        return f"entity:{chat}"


class ChatRefTest(unittest.TestCase):
    def test_an_id_typed_as_text_becomes_a_number(self):
        # Telethon takes the text "-1001234567890" for a phone number and fails to find it.
        self.assertEqual(chat_ref("-1001234567890"), -1001234567890)
        self.assertEqual(chat_ref(" 12345 "), 12345)

    def test_usernames_and_links_stay_text(self):
        self.assertEqual(chat_ref("@news"), "@news")
        self.assertEqual(chat_ref("https://t.me/news"), "https://t.me/news")


class CachedEntityTest(unittest.IsolatedAsyncioTestCase):
    async def test_a_username_goes_through_the_session_cache(self):
        # get_entity("@news") would ask Telegram to resolve the username every time; that request is rate limited.
        client = FakeClient()
        self.assertEqual(await cached_entity(client, "@news"), "entity:input:@news")
        self.assertEqual(client.calls, [("input", "@news"), ("entity", "input:@news")])

    async def test_an_id_from_the_list_is_looked_up_as_a_number(self):
        client = FakeClient()
        await cached_entity(client, "-1001234567890")
        self.assertEqual(client.calls[0], ("input", -1001234567890))


if __name__ == "__main__":
    unittest.main()
