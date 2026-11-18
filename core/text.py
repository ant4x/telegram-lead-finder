"""Text for bot messages. Telegram HTML needs <, > and & escaped, and one message holds at most 4096 characters."""
from html import escape

MESSAGE_LIMIT = 4096


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
