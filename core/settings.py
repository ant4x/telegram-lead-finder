from environs import Env
from dataclasses import dataclass, field

from core.leads.ai import AiConfig
from core.modules import parse_modules


@dataclass
class Bots:
    bot_token: str
    admins_id: list[int] = field(default_factory=list)


@dataclass
class Telethon:
    api_id: int
    api_hash: str


@dataclass
class Settings:
    bots: Bots
    telethon: Telethon
    modules: frozenset[str]
    ai: AiConfig


def get_settings(path: str):
    env = Env()
    env.read_env(path)

    return Settings(
        bots=Bots(
            bot_token=env.str("TOKEN"),
            admins_id=env.list("ADMINS_ID", subcast=int)
        ),
        telethon=Telethon(
            api_id=env.int("API_ID"),
            api_hash=env.str("API_HASH")
        ),
        # Empty values mean the defaults, which parse_modules and check_lead fill in: environs keeps an empty value.
        modules=parse_modules(env.list("MODULES", [])),
        # No default model: which one to use is the owner's choice and changes as better ones come out.
        ai=AiConfig(
            api_key=env.str("AI_API_KEY", ""),
            model=env.str("AI_MODEL", ""),
            base_url=env.str("AI_BASE_URL", "")
        )
    )


settings = get_settings('.env')
