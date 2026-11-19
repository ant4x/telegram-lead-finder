"""/lead_stats: what came from each chat in 30 days and what the owner made of it, to see which chats are worth it."""
from html import escape

from core.text import plural

STATS_SECONDS = 30 * 24 * 3600


def stats_lines(rows: list[tuple[str, int, int, int, int, int]]) -> list[str]:
    return [f"▪️ <b>{escape(title)}</b>: {plural(alerts, 'alert')} · {replied} replied · "
            f"{plural(not_lead, 'not lead')} · {unmarked} unmarked" + (f" · {dropped} dropped by AI" if dropped else "")
            for title, alerts, replied, not_lead, unmarked, dropped in rows]
