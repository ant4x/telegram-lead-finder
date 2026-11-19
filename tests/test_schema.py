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


class LeadTablesTest(unittest.TestCase):
    """Niches belong to a user and keep their words; leads belong to a watched chat."""

    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        self.db.execute("INSERT INTO channels (channel_id, username, title) VALUES (-1001, 'web', 'Web chat')")
        self.db.execute("INSERT INTO niches (owner_id, name) VALUES (10, 'Websites')")
        self.db.execute("INSERT INTO niche_words (niche_id, word) VALUES (1, 'сайт*')")
        self.db.execute(
            "INSERT INTO leads (owner_id, channel_db_id, message_id, link, author, kind, text, text_hash, created_at)"
            " VALUES (10, 1, 5, 'https://t.me/web/5', '@ann', 'request', 'Нужен сайт', 'h', 1700000000)"
        )

    def tearDown(self):
        self.db.close()

    def count(self, table):
        return self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def test_deleting_a_niche_deletes_its_words(self):
        self.db.execute("DELETE FROM niches WHERE id = 1")
        self.assertEqual(self.count("niche_words"), 0)

    def test_deleting_a_channel_deletes_its_leads(self):
        self.db.execute("DELETE FROM channels WHERE id = 1")
        self.assertEqual(self.count("leads"), 0)

    def test_one_owner_cannot_have_two_niches_with_one_name(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO niches (owner_id, name) VALUES (10, 'Websites')")

    def test_two_owners_can_use_the_same_niche_name(self):
        self.db.execute("INSERT INTO niches (owner_id, name) VALUES (20, 'Websites')")
        self.assertEqual(self.count("niches"), 2)


if __name__ == "__main__":
    unittest.main()
