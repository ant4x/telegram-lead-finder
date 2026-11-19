import logging

import aiosqlite
from typing import Any

from core.database.schema import SCHEMA
from core.leads.preferences import DEFAULT_SETTINGS, LeadSettings
from core.leads.rules import KINDS, Niche


DB_NAME = "shillometer.db"


async def execute_query(query, params=None, commit=True, fetchall=False, fetchone=False) -> Any:
    async with aiosqlite.connect(DB_NAME) as connection:
        await connection.execute("PRAGMA foreign_keys = ON")
        async with connection.cursor() as cursor:
            await cursor.execute(query, params or ())
            if commit:
                await connection.commit()

            if fetchall:
                return await cursor.fetchall()
            if fetchone:
                return await cursor.fetchone()
    return None


async def execute_changes(query, params=None) -> int:
    """Runs a write and returns how many rows it changed: 0 when a WHERE matched nothing or a row was ignored."""
    async with aiosqlite.connect(DB_NAME) as connection:
        await connection.execute("PRAGMA foreign_keys = ON")
        async with connection.cursor() as cursor:
            await cursor.execute(query, params or ())
            await connection.commit()
            return cursor.rowcount


async def create_tables():
    async with aiosqlite.connect(DB_NAME) as connection:
        await connection.executescript(SCHEMA)
    logging.info("Database tables are ready")


async def add_channel(channel_id: int, username: str, title: str) -> str:
    query_select = "SELECT 1 FROM channels WHERE channel_id = ?"
    existing = await execute_query(query_select, (channel_id,), fetchone=True)

    if existing:
        return 'exists'

    query_insert = "INSERT INTO channels (channel_id, username, title) VALUES (?, ?, ?)"
    await execute_query(query_insert, (channel_id, username, title))
    return 'added'


async def get_all_channels() -> list[str | int]:
    query = "SELECT username, channel_id FROM channels"
    results = await execute_query(query, fetchall=True)
    if not results:
        return []

    identifiers = []
    for username, channel_id in results:
        if username:
            identifiers.append(f"@{username}")
        else:
            identifiers.append(channel_id)

    return identifiers


async def find_channel_db_id_by_telegram_id(telegram_id: int) -> int | None:
    query = "SELECT id FROM channels WHERE channel_id = ?"
    result = await execute_query(query, (telegram_id,), fetchone=True)
    return result[0] if result else None


async def get_all_channels_with_details() -> list[tuple[int, str, str]]:
    query = "SELECT id, title, CASE WHEN username IS NOT NULL THEN ('@' || username) ELSE CAST(channel_id AS TEXT) END FROM channels ORDER BY title"
    return await execute_query(query, fetchall=True)


async def add_project(name: str) -> str:
    name_lower = name.lower()
    existing = await execute_query("SELECT 1 FROM projects WHERE name = ?", (name_lower,), fetchone=True)
    if existing:
        return 'exists'

    await execute_query("INSERT INTO projects (name) VALUES (?)", (name_lower,))
    return 'added'


async def get_all_projects() -> list[tuple[int, str]]:
    query = "SELECT id, name FROM projects ORDER BY name"
    results = await execute_query(query, fetchall=True)
    return results if results else []


async def delete_channel_by_id(db_id: int):
    query = "DELETE FROM channels WHERE id = ?"
    await execute_query(query, (db_id,))


async def find_channel(channel_id: int) -> tuple | None:
    query = "SELECT id, title FROM channels WHERE channel_id = ?"
    return await execute_query(query, (channel_id,), fetchone=True)


async def delete_project_by_id(db_id: int):
    await execute_query("DELETE FROM projects WHERE id = ?", (db_id,))


async def save_post(channel_db_id: int, message_id: int, link: str, post_date, text: str) -> int:
    return await execute_insert("INSERT INTO posts (channel_db_id, message_id, link, post_date, text)"
                                " VALUES (?, ?, ?, ?, ?)", (channel_db_id, message_id, link, post_date, text))


async def log_mention(post_db_id: int, project_db_id: int):
    query = "INSERT INTO mentions (post_db_id, project_db_id) VALUES (?, ?)"
    await execute_query(query, (post_db_id, project_db_id))


async def add_niche(owner_id: int, name: str) -> int:
    """The id of the owner's niche with this name, created if it is new."""
    await execute_query("INSERT OR IGNORE INTO niches (owner_id, name) VALUES (?, ?)", (owner_id, name))
    row = await execute_query("SELECT id FROM niches WHERE owner_id = ? AND name = ?", (owner_id, name), fetchone=True)
    return row[0]


async def add_niche_word(niche_id: int, word: str) -> str:
    """'added', or 'exists' when the niche has the word already. Words are kept in lower case."""
    changed = await execute_changes("INSERT OR IGNORE INTO niche_words (niche_id, word) VALUES (?, ?)",
                                    (niche_id, word.lower()))
    return 'added' if changed else 'exists'


async def get_niches(owner_id: int | None = None) -> list[Niche]:
    """The owner's niches with their words, by name; every owner's when owner_id is None."""
    query = ("SELECT n.id, n.owner_id, n.name, w.word FROM niches n LEFT JOIN niche_words w ON w.niche_id = n.id"
             + ("" if owner_id is None else " WHERE n.owner_id = ?") + " ORDER BY n.name, n.id, w.word")
    rows = await execute_query(query, () if owner_id is None else (owner_id,), fetchall=True)
    niches: dict[int, Niche] = {}
    for niche_id, owner, name, word in rows:
        niche = niches.get(niche_id, Niche(niche_id, owner, name, ()))
        niches[niche_id] = Niche(niche_id, owner, name, niche.words + ((word,) if word else ()))
    return list(niches.values())


async def delete_niche(niche_id: int, owner_id: int) -> bool:
    """Deletes the niche with its words if it belongs to the owner; False when it does not or is gone."""
    return await execute_changes("DELETE FROM niches WHERE id = ? AND owner_id = ?", (niche_id, owner_id)) > 0


async def execute_insert(query, params) -> int:
    """Runs an INSERT and returns the id of the new row."""
    async with aiosqlite.connect(DB_NAME) as connection:
        await connection.execute("PRAGMA foreign_keys = ON")
        async with connection.cursor() as cursor:
            await cursor.execute(query, params)
            await connection.commit()
            return cursor.lastrowid


async def save_lead(owner_id: int, channel_db_id: int, message_id: int, link: str, author: str, kind: str, text: str,
                    text_hash: str, created_at: int, ai_author: str | None = None, summary: str | None = None,
                    verdict: str | None = None) -> int:
    return await execute_insert(
        "INSERT INTO leads (owner_id, channel_db_id, message_id, link, author, kind, text, text_hash, created_at,"
        " ai_author, summary, verdict) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (owner_id, channel_db_id, message_id, link, author, kind, text, text_hash, created_at, ai_author, summary,
         verdict))


async def seen_recently(owner_id: int, text_hash: str, since: int) -> bool:
    """Whether the owner has a lead with this text since the given time."""
    row = await execute_query("SELECT 1 FROM leads WHERE owner_id = ? AND text_hash = ? AND created_at >= ? LIMIT 1",
                              (owner_id, text_hash, since), fetchone=True)
    return row is not None


async def set_lead_verdict(lead_id: int, owner_id: int, verdict: str) -> bool:
    """Marks the owner's lead; False when the lead is someone else's or gone."""
    return await execute_changes("UPDATE leads SET verdict = ? WHERE id = ? AND owner_id = ?",
                                 (verdict, lead_id, owner_id)) > 0


async def purge_old_leads(before: int) -> int:
    """Erases the text, author and links of leads older than the given time and returns how many; counts stay."""
    return await execute_changes(
        "UPDATE leads SET text = NULL, author = NULL, summary = NULL, link = NULL, message_id = NULL, text_hash = NULL"
        " WHERE created_at < ? AND link IS NOT NULL", (before,))


async def get_lead_settings(user_id: int) -> LeadSettings:
    """The user's lead settings; the defaults until they change something."""
    row = await execute_query("SELECT kinds, ai_mode FROM lead_settings WHERE user_id = ?", (user_id,), fetchone=True)
    if not row:
        return DEFAULT_SETTINGS
    kinds, ai_mode = row
    return LeadSettings(frozenset(kind for kind in kinds.split(",") if kind), ai_mode)


async def save_lead_settings(user_id: int, settings: LeadSettings):
    kinds = ",".join(kind for kind in KINDS if kind in settings.kinds)
    await execute_query(
        "INSERT INTO lead_settings (user_id, kinds, ai_mode) VALUES (?, ?, ?)"
        " ON CONFLICT (user_id) DO UPDATE SET kinds = excluded.kinds, ai_mode = excluded.ai_mode",
        (user_id, kinds, settings.ai_mode))


async def lead_stats(owner_id: int, since: int) -> list[tuple[str, int, int, int, int, int]]:
    """
    Per chat since the given time, most alerts first: the chat, alerts sent, marked "I'll reply", marked
    "Not a lead", left unmarked, and dropped by the AI filter (those are not alerts).
    """
    return await execute_query(
        "SELECT c.title, SUM(l.verdict IS NOT 'ai_dropped'), SUM(l.verdict IS 'reply'), SUM(l.verdict IS 'not_lead'),"
        " SUM(l.verdict IS NULL), SUM(l.verdict IS 'ai_dropped')"
        " FROM leads l JOIN channels c ON c.id = l.channel_db_id"
        " WHERE l.owner_id = ? AND l.created_at >= ? GROUP BY c.id ORDER BY 2 DESC, c.title",
        (owner_id, since), fetchall=True)


async def record_ai_verdict(lead_id: int, kind: str, ai_author: str, summary: str, verdict: str | None = None):
    """Adds the AI's answer to a saved lead: its kind, who writes, what they need, and 'ai_dropped' if filtered."""
    await execute_query("UPDATE leads SET kind = ?, ai_author = ?, summary = ?, verdict = ? WHERE id = ?",
                        (kind, ai_author, summary, verdict, lead_id))
