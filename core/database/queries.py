import logging

import aiosqlite
from typing import Any

from core.database.schema import SCHEMA


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


async def seed_initial_channels(resolve, channels_to_seed: list):
    existing_channels = await get_all_channels()
    if existing_channels:
        return

    for channel_input in channels_to_seed:
        try:
            channel_id, username, title = await resolve(channel_input)
            await add_channel(channel_id=channel_id, username=username, title=title)
        except Exception as e:
            logging.warning(f"Seed channel {channel_input} was not added: {e}")
    logging.info("Seed channels added")


async def delete_channel_by_id(db_id: int):
    query = "DELETE FROM channels WHERE id = ?"
    await execute_query(query, (db_id,))


async def find_channel(channel_id: int) -> tuple | None:
    query = "SELECT id, title FROM channels WHERE channel_id = ?"
    return await execute_query(query, (channel_id,), fetchone=True)


async def delete_project_by_id(db_id: int):
    await execute_query("DELETE FROM projects WHERE id = ?", (db_id,))


async def save_post(channel_db_id: int, message_id: int, link: str, post_date, text: str) -> int:
    query = """
        INSERT INTO posts (channel_db_id, message_id, link, post_date, text)
        VALUES (?, ?, ?, ?, ?)
    """

    async with aiosqlite.connect(DB_NAME) as connection:
        await connection.execute("PRAGMA foreign_keys = ON")
        async with connection.cursor() as cursor:
            await cursor.execute(query, (channel_db_id, message_id, link, post_date, text))
            await connection.commit()
            return cursor.lastrowid


async def log_mention(post_db_id: int, project_db_id: int):
    query = "INSERT INTO mentions (post_db_id, project_db_id) VALUES (?, ?)"
    await execute_query(query, (post_db_id, project_db_id))
