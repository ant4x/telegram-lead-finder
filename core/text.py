"""
Text helpers without Telegram: keyword matching, post links and message formatting.
Telegram HTML needs <, > and & escaped, and one message holds at most 4096 characters.
"""
import re
from html import escape

MESSAGE_LIMIT = 4096
INVALID_KEYWORD = "⚠️ Use 2 to 99 characters, with at least one letter or digit. Try again, or send /cancel."


def valid_keyword(keyword: str) -> bool:
    """2 to 99 characters with at least one letter or digit: a name of stars or punctuation would match every post."""
    return 1 < len(keyword) < 100 and re.search(r"\w", keyword) is not None


def mentions(text: str, keyword: str) -> bool:
    """
    Whether the text names the keyword as a whole word or phrase, in any case: "ton" is found in "TON is up",
    not in "button". Inflected forms are other words, so "сайт" does not find "сайта". A keyword ending in *
    finds every word that starts with it: "сайт*" finds "сайт", "сайта" and "сайтом".
    """
    whole_word = not keyword.endswith("*")
    pattern = rf"(?<!\w){re.escape(keyword.rstrip('*'))}" + (r"(?!\w)" if whole_word else "")
    return re.search(pattern, text, re.IGNORECASE) is not None


def quote(text: str, limit: int = 200) -> str:
    """The start of a post for a notification, escaped for HTML."""
    if len(text) <= limit:
        return escape(text)
    return escape(text[:limit]) + "..."


def split_message(header: str, lines: list[str], limit: int = MESSAGE_LIMIT) -> list[str]:
    """The header and the lines, one per row, cut into messages that fit the limit."""
    messages, current = [], header
    for line in lines:
        if len(current) + 1 + len(line) > limit:
            messages.append(current)
            current = line
        else:
            current = f"{current}\n{line}"
    messages.append(current)
    return messages


def post_link(username: str | None, channel_id: int, message_id: int) -> str:
    """A link to a post. Private channels have no username: their links use the channel's own id, without -100."""
    if username:
        return f"https://t.me/{username}/{message_id}"
    return f"https://t.me/c/{channel_id}/{message_id}"
