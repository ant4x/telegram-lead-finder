import unittest
from unittest import mock

from core.database.queries import add_niche, delete_niche
from core.handlers.niche_handlers import process_niche_word
from tests.db import DbTestCase


class NicheWordTest(DbTestCase):
    async def test_a_word_for_a_deleted_niche_ends_the_step(self):
        niche_id = await add_niche(10, "Websites")
        await delete_niche(niche_id, 10)
        state = mock.AsyncMock()
        state.get_data.return_value = {"niche_id": niche_id}
        message = mock.AsyncMock(text="SEO")
        await process_niche_word(message, state)
        state.clear.assert_awaited_once()
        self.assertIn("removed", message.answer.await_args.args[0])


if __name__ == "__main__":
    unittest.main()
