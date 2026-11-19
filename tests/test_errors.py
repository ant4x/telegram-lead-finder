import unittest
from unittest import mock

from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageReplyMarkup
from aiogram.types import ErrorEvent, Update

from core.handlers.errors import UNCHANGED, unchanged_message


def error_event(text: str) -> ErrorEvent:
    exception = TelegramBadRequest(EditMessageReplyMarkup(chat_id=1, message_id=1), text)
    return ErrorEvent(update=Update(update_id=1), exception=exception)


class UnchangedMessageTest(unittest.IsolatedAsyncioTestCase):
    """A second tap on a button asks Telegram to redraw a message that has not changed."""

    async def test_catches_only_an_edit_that_changes_nothing(self):
        self.assertTrue(await UNCHANGED(error_event("Bad Request: message is not modified: specified new message "
                                                    "content and reply markup are exactly the same")))
        self.assertFalse(await UNCHANGED(error_event("Bad Request: message to edit not found")))

    async def test_answers_the_tap_so_the_button_stops_spinning(self):
        callback = mock.AsyncMock()
        await unchanged_message(mock.Mock(update=mock.Mock(callback_query=callback)))
        callback.answer.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
