"""The bot's commands: one list for the command menu and the /start message, filtered by the enabled modules."""
from dataclasses import dataclass
from html import escape

from core.limits import SEARCHES_PER_DAY
from core.modules import MODULES


@dataclass(frozen=True)
class Command:
    name: str
    emoji: str
    description: str
    admin: bool
    module: str | None  # None: on whatever modules are enabled


COMMANDS = (
    Command("start", "▶️", "Show the commands", False, None),
    Command("analyze", "📊", f"Search past posts for a project ({SEARCHES_PER_DAY} a day)", False, "mentions"),
    Command("cancel", "🛑", "Stop the current step", False, None),
    Command("add_channel", "➕", "Add a channel or group", True, None),
    Command("del_channel", "➖", "Remove a channel or group", True, None),
    Command("list_channels", "📋", "List watched channels and groups", True, None),
    Command("add_project", "🧐", "Watch a project", True, "mentions"),
    Command("del_project", "😒", "Stop watching a project", True, "mentions"),
    Command("list_projects", "📋", "List watched projects", True, "mentions"),
    Command("add_niche", "🎯", "Add a niche: a topic and its words", True, "leads"),
    Command("list_niches", "📋", "List your niches", True, "leads"),
    Command("del_niche", "🗑", "Remove a niche", True, "leads"),
    Command("lead_settings", "⚙️", "Choose which leads to get", True, "leads"),
    Command("check_chat", "🔎", "Check a chat's recent history for leads", True, "leads"),
    Command("lead_stats", "📈", "Lead statistics for 30 days", True, "leads"),
)

TAGLINES = {
    "mentions": "📡 <i>Everyone shilling the same project? See who, where and how often.</i>",
    "leads": "🎯 <i>Someone in your chats needs what you offer? Get an alert, then reply from your own account.</i>",
}


def enabled_commands(modules: frozenset[str]) -> list[Command]:
    return [command for command in COMMANDS if command.module is None or command.module in modules]


def _line(command: Command) -> str:
    return f"{command.emoji} <b>/{command.name}</b>: {command.description[0].lower()}{command.description[1:]}"


def start_text(first_name: str, modules: frozenset[str]) -> str:
    """The /start message: a line about each enabled module, then its commands for everyone and for admins."""
    commands = enabled_commands(modules)
    return "\n".join([
        f"👋 <b>Hi, {escape(first_name)}!</b>",
        "",
        *(TAGLINES[module] for module in MODULES if module in modules),
        "",
        "<b>📌 Commands</b>",
        *(_line(command) for command in commands if not command.admin),
        "",
        "<i><b>FOR ADMINS</b></i>",
        *(_line(command) for command in commands if command.admin),
    ])
