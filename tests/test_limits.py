import unittest
from datetime import date

from core.limits import DailyLimit


class DailyLimitTest(unittest.TestCase):
    today = date(2026, 11, 19)

    def test_a_new_user_has_the_whole_limit(self):
        self.assertEqual(DailyLimit(3).left(1, self.today), 3)

    def test_each_use_takes_one(self):
        limit = DailyLimit(3)
        for _ in range(3):
            limit.use(1, self.today)
        self.assertEqual(limit.left(1, self.today), 0)

    def test_the_limit_comes_back_the_next_day(self):
        limit = DailyLimit(3)
        for _ in range(3):
            limit.use(1, self.today)
        self.assertEqual(limit.left(1, date(2026, 11, 20)), 3)

    def test_users_are_counted_apart(self):
        limit = DailyLimit(3)
        limit.use(1, self.today)
        self.assertEqual((limit.left(1, self.today), limit.left(2, self.today)), (2, 3))


if __name__ == "__main__":
    unittest.main()
