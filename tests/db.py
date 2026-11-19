import os
import tempfile
import unittest
from unittest import mock

from core.database import queries


class DbTestCase(unittest.IsolatedAsyncioTestCase):
    """Each test gets a fresh database file, with the tables the bot creates at startup."""

    async def asyncSetUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patcher = mock.patch.object(queries, "DB_NAME", os.path.join(folder.name, "test.db"))
        patcher.start()
        self.addCleanup(patcher.stop)
        await queries.create_tables()
