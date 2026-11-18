"""Tables of the bot. Deleting a channel or a project also deletes the posts and mentions recorded for it."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    title TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    link TEXT,
    post_date DATETIME NOT NULL,
    text TEXT,
    channel_db_id INTEGER,
    FOREIGN KEY (channel_db_id) REFERENCES channels (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_db_id INTEGER,
    project_db_id INTEGER,
    FOREIGN KEY (post_db_id) REFERENCES posts (id) ON DELETE CASCADE,
    FOREIGN KEY (project_db_id) REFERENCES projects (id) ON DELETE CASCADE
);
"""
