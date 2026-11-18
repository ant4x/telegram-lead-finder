from telethon import TelegramClient, utils
from telethon.tl.types import Channel
from core.settings import settings


client = TelegramClient(
    'my_monitor_session',
    settings.telethon.api_id,
    settings.telethon.api_hash
)


async def resolve_channel(channel_input) -> tuple[int, str | None, str]:
    """
    A channel or a group by username, link or id: its id in the form updates carry (-100...), username and title.
    Raises ValueError for anything that is not a channel or a group.
    """
    entity = await client.get_entity(channel_input)
    if not isinstance(entity, Channel):
        raise ValueError(f"{channel_input} is not a channel")
    return utils.get_peer_id(entity), entity.username, entity.title
