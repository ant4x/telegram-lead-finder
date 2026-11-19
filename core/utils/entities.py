"""
Looking chats up without spending Telegram's limits. get_entity("@name") asks Telegram to resolve the username
every time, and those requests are limited hard; get_input_entity looks in the session's cache first and asks
Telegram only for a chat it has not seen. Telethon takes an id typed as text for a phone number, so it becomes
a number first.
"""
import re

ID = re.compile(r"-?\d+")


def chat_ref(chat: str | int) -> str | int:
    """The chat as Telethon should get it: a number for an id, even one typed as text; the text otherwise."""
    if isinstance(chat, str) and ID.fullmatch(chat.strip()):
        return int(chat)
    return chat


async def cached_entity(client, chat: str | int):
    """The chat or group, from the session's cache when it is there."""
    return await client.get_entity(await client.get_input_entity(chat_ref(chat)))
