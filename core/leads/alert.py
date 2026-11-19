"""The alert about a lead: what it is, where and who wrote it, a quote and links. Strangers' text is escaped."""
from dataclasses import dataclass
from html import escape

from core.text import quote

KIND_LABELS = {"request": "Request", "problem": "Problem", "vacancy": "Vacancy"}
QUOTE_LIMIT = 300


@dataclass(frozen=True)
class Author:
    name: str
    url: str | None  # a link to message the author: only for users with a username


def author_of(sender, chat_title: str) -> Author:
    """
    Who wrote the message. Channels, including those that repost orders, and anonymous group admins write as a
    chat, so the chat is the author and the client's contact is in the text. Links of the form tg://user?id=
    are left out: the Bot API guarantees them only for people who have written to the bot themselves.
    """
    if sender is None or getattr(sender, "title", None):
        return Author(getattr(sender, "title", None) or chat_title, None)
    if sender.username:
        return Author(f"@{sender.username}", f"https://t.me/{sender.username}")
    name = " ".join(part for part in (sender.first_name, sender.last_name) if part)
    return Author(name or "Someone", None)


def alert_text(kind: str, niche_names: list[str], chat_title: str, author: Author, text: str, link: str,
               ai_line: str | None = None) -> str:
    links = f"<a href='{escape(link)}'>Open the message</a>"
    if author.url:
        links += f" · <a href='{escape(author.url)}'>Message the author</a>"
    return "\n".join([
        f"🎯 <b>Lead</b> · {escape(', '.join(niche_names))} · {KIND_LABELS[kind]}",
        f"<b>Chat:</b> {escape(chat_title)}",
        f"<b>From:</b> {escape(author.name)}",
        "",
        f"<i>“{quote(text, QUOTE_LIMIT)}”</i>",
        *([ai_line] if ai_line else []),
        "",
        links,
    ])
