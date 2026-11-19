"""
Tables of the bot. Deleting a channel or a project also deletes the posts and mentions recorded for it.
The lead finder keeps niches with their words, each user's lead settings and the leads found. Leads belong
to a watched chat and go when it is removed; their text, author and links are erased after 30 days.
"""

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

CREATE TABLE IF NOT EXISTS niches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (owner_id, name)
);

CREATE TABLE IF NOT EXISTS niche_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    niche_id INTEGER NOT NULL,
    word TEXT NOT NULL,
    UNIQUE (niche_id, word),
    FOREIGN KEY (niche_id) REFERENCES niches (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lead_settings (
    user_id INTEGER PRIMARY KEY,
    kinds TEXT NOT NULL,
    ai_mode TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    channel_db_id INTEGER NOT NULL,
    message_id INTEGER,
    link TEXT,
    author TEXT,
    kind TEXT NOT NULL,
    ai_author TEXT,
    summary TEXT,
    text TEXT,
    text_hash TEXT,
    created_at INTEGER NOT NULL,
    verdict TEXT,
    FOREIGN KEY (channel_db_id) REFERENCES channels (id) ON DELETE CASCADE
);
"""
