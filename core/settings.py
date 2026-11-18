from environs import Env
from dataclasses import dataclass, field
from typing import List


@dataclass
class Bots:
    bot_token: str
    admins_id: List[int] = field(default_factory=list)


@dataclass
class Telethon:
    api_id: int
    api_hash: str


@dataclass
class Settings:
    bots: Bots
    telethon: Telethon


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
        )
    )


settings = get_settings('.env')
