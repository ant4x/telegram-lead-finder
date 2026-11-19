"""Each user's lead settings: which kinds of leads to get and how the AI check works (off, labels or a filter)."""
from dataclasses import dataclass, replace

from core.leads.rules import KINDS

AI_MODES = ("off", "labels", "filter")
KIND_NAMES = {"request": "Requests", "vacancy": "Vacancies", "problem": "Problems"}
KIND_HINTS = {
    "request": "someone asks for what you do",
    "vacancy": "a company hires for it",
    "problem": "someone has a problem you can fix",
}


@dataclass(frozen=True)
class LeadSettings:
    kinds: frozenset[str]
    ai_mode: str


DEFAULT_SETTINGS = LeadSettings(frozenset(KINDS), "labels")


def toggle_kind(settings: LeadSettings, kind: str) -> LeadSettings:
    return replace(settings, kinds=settings.kinds ^ {kind})


def settings_text(settings: LeadSettings) -> str:
    lines = ["⚙️ <b>Lead settings</b>", "", "Tap a kind to turn it on or off:"]
    lines += [f"{'✅' if kind in settings.kinds else '▫️'} {KIND_NAMES[kind]}: {KIND_HINTS[kind]}" for kind in KINDS]
    if not settings.kinds:
        lines += ["", "⚠️ Every kind is off. No lead alerts will come."]
    return "\n".join(lines)
