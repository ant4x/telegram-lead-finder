import aiosqlite
from typing import List, Tuple, Any, Union


DB_NAME = "shillometr.db"


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
    await execute_query("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT
        )
    """)

    await execute_query("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                title TEXT NOT NULL
            )
        """)

    await execute_query("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

    await execute_query("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                link TEXT,
                post_date DATETIME NOT NULL,
                text TEXT,
                channel_db_id INTEGER,
                FOREIGN KEY (channel_db_id) REFERENCES channels (id)
            )
        """)

    await execute_query("""
            CREATE TABLE IF NOT EXISTS mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_db_id INTEGER,
                project_db_id INTEGER,
                FOREIGN KEY (post_db_id) REFERENCES posts (id),
                FOREIGN KEY (project_db_id) REFERENCES projects (id)
            )
        """)
    print("База данных и таблицы успешно проверены/созданы.")


# ---КАНАЛЫ---


async def add_channel(channel_id: int, username: str, title: str) -> str:
    query_select = "SELECT 1 FROM channels WHERE channel_id = ?"
    existing = await execute_query(query_select, (channel_id,), fetchone=True)

    if existing:
        print(f"Попытка добавить существующий канал '{title}'.")
        return 'exists'

    query_insert = "INSERT INTO channels (channel_id, username, title) VALUES (?, ?, ?)"
    await execute_query(query_insert, (channel_id, username, title))
    print(f"Канал '{title}' добавлен в базу данных.")
    return 'added'


async def get_all_channels() -> List[Union[str, int]]:
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


async def get_all_channels_with_details() -> List[Tuple[int, str, str]]:
    query = "SELECT id, title, CASE WHEN username IS NOT NULL THEN ('@' || username) ELSE CAST(channel_id AS TEXT) END FROM channels ORDER BY title"
    return await execute_query(query, fetchall=True)


# ---ПРОЕКТЫ---


async def add_project(name: str) -> str:
    name_lower = name.lower()
    existing = await execute_query("SELECT 1 FROM projects WHERE name = ?", (name_lower,), fetchone=True)
    if existing:
        return 'exists'

    await execute_query("INSERT INTO projects (name) VALUES (?)", (name_lower,))
    return 'added'


async def get_all_projects() -> List[Tuple[int, str]]:
    query = "SELECT id, name FROM projects ORDER BY name"
    results = await execute_query(query, fetchall=True)
    return results if results else []


async def register_user(user_id: int, username: str, first_name: str):
    query_select = "SELECT 1 FROM users WHERE user_id = ?"
    existing = await execute_query(query_select, (user_id,), fetchone=True)
    if not existing:
        query_insert = "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)"
        await execute_query(query_insert, (user_id, username, first_name))


async def seed_initial_channels(client, channels_to_seed: list):
    existing_channels = await get_all_channels()
    if existing_channels:
        print("База данных каналов уже наполнена. Пропускаю начальное наполнение.")
        return

    print("База данных каналов пуста. Начинаю начальное наполнение...")
    for channel_input in channels_to_seed:
        try:
            entity = await client.get_entity(channel_input)

            channel_id = entity.id
            if hasattr(entity, 'broadcast') and entity.broadcast:
                if not str(channel_id).startswith('-100'):
                    channel_id = int(f"-100{channel_id}")

            username = getattr(entity, 'username', None)
            title = entity.title

            await add_channel(channel_id=channel_id, username=username, title=title)
        except Exception as e:
            print(f"Не удалось добавить '{channel_input}': {e}")
    print("Начальное наполнение базы каналов завершено.")


async def delete_channel_by_id(db_id: int) -> bool:
    query = "DELETE FROM channels WHERE id = ?"
    await execute_query(query, (db_id,))
    return True


async def find_channel_by_identifier(identifier) -> tuple | None:
    if isinstance(identifier, int):
        query = "SELECT id, title FROM channels WHERE channel_id = ?"
        return await execute_query(query, (identifier,), fetchone=True)
    elif isinstance(identifier, str):
        query = "SELECT id, title FROM channels WHERE username = ?"
        return await execute_query(query, (identifier.replace('@', ''),), fetchone=True)
    return None


async def delete_project_by_id(db_id: int) -> bool:
    await execute_query("DELETE FROM projects WHERE id = ?", (db_id,))
    return True


# --- ФУНКЦИИ ДЛЯ СОХРАНЕНИЯ РЕЗУЛЬТАТОВ МОНИТОРИНГА ---


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
