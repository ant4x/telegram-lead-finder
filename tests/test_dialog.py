import unittest
from unittest import mock

from core.handlers.dialog import cancel_dialog


def fake_state(current: str | None) -> mock.AsyncMock:
    state = mock.AsyncMock()
    state.get_state.return_value = current
    return state


class CancelTest(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_ends_the_current_step(self):
        state, message = fake_state("NicheStates:waiting_for_word"), mock.AsyncMock()
        await cancel_dialog(message, state)
        state.clear.assert_awaited_once()
        self.assertIn("Canceled", message.answer.await_args.args[0])

    async def test_cancel_outside_a_step_still_answers(self):
        # /cancel is in the command menu, so a tap on it outside a dialog must not meet silence.
        message = mock.AsyncMock()
        await cancel_dialog(message, fake_state(None))
        self.assertIn("Nothing to cancel", message.answer.await_args.args[0])


if __name__ == "__main__":
    unittest.main()
