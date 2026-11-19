import unittest

from core.monitoring.listener import dispatch


class DispatchTest(unittest.IsolatedAsyncioTestCase):
    async def test_a_failing_handler_does_not_stop_the_next(self):
        seen = []

        async def failing(event):
            raise RuntimeError("broken module")

        async def working(event):
            seen.append(event)

        with self.assertLogs(level="ERROR") as logs:
            await dispatch("new message", [failing, working])
        self.assertEqual(seen, ["new message"])
        self.assertIn("broken module", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
