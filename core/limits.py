"""
How much people who are not admins may use the history search: it reads channels through the owner's Telegram
account, so strangers get a few searches a day over a short period. Admins have no limits.
"""
from datetime import date

SEARCHES_PER_DAY = 3
MAX_DAYS = 30


class DailyLimit:
    """Counts uses per user and calendar day, in memory: a restart of the bot starts the count again."""

    def __init__(self, per_day: int):
        self.per_day = per_day
        self.used: dict[int, tuple[date, int]] = {}

    def left(self, user_id: int, today: date) -> int:
        day, count = self.used.get(user_id, (today, 0))
        return self.per_day - (count if day == today else 0)

    def use(self, user_id: int, today: date):
        self.used[user_id] = (today, self.per_day - self.left(user_id, today) + 1)
