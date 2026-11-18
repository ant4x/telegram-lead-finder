import sqlite3
import unittest

from core.database.schema import SCHEMA


class DeletionTest(unittest.TestCase):
    """The bot keeps foreign keys on, so deleting a row others refer to must not fail."""

    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        self.db.execute("INSERT INTO channels (channel_id, username, title) VALUES (-1001, 'news', 'News')")
        self.db.execute("INSERT INTO projects (name) VALUES ('acme')")
        self.db.execute(
            "INSERT INTO posts (message_id, link, post_date, text, channel_db_id)"
            " VALUES (7, 'https://t.me/news/7', '2026-01-01', 'acme is out', 1)"
        )
        self.db.execute("INSERT INTO mentions (post_db_id, project_db_id) VALUES (1, 1)")

    def tearDown(self):
        self.db.close()

    def count(self, table):
        return self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def test_deleting_a_channel_deletes_its_posts_and_mentions(self):
        self.db.execute("DELETE FROM channels WHERE id = 1")
        self.assertEqual((self.count("posts"), self.count("mentions")), (0, 0))

    def test_deleting_a_project_deletes_its_mentions_and_keeps_the_posts(self):
        self.db.execute("DELETE FROM projects WHERE id = 1")
        self.assertEqual((self.count("posts"), self.count("mentions")), (1, 0))


if __name__ == "__main__":
    unittest.main()
