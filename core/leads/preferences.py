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
AI_MODE_NAMES = {"off": "Off", "labels": "Labels", "filter": "Filter"}
AI_MODE_HINTS = {
    "off": "leads come by the rules alone",
    "labels": "everything the rules find, with the AI's note on who writes and what they need",
    "filter": "only what the AI confirms as a lead",
}


@dataclass(frozen=True)
class LeadSettings:
    kinds: frozenset[str]
    ai_mode: str


DEFAULT_SETTINGS = LeadSettings(frozenset(KINDS), "labels")


def toggle_kind(settings: LeadSettings, kind: str) -> LeadSettings:
    return replace(settings, kinds=settings.kinds ^ {kind})


def mark(on: bool) -> str:
    return "✅" if on else "▫️"


def settings_text(settings: LeadSettings, ai_available: bool) -> str:
    """The settings message: the kinds, then the AI modes, or how to turn the AI check on."""
    lines = ["⚙️ <b>Lead settings</b>", "", "Tap a kind to turn it on or off:"]
    lines += [f"{mark(kind in settings.kinds)} {KIND_NAMES[kind]}: {KIND_HINTS[kind]}" for kind in KINDS]
    if not settings.kinds:
        lines += ["", "⚠️ Every kind is off. No lead alerts will come."]
    lines.append("")
    if ai_available:
        lines.append("🤖 AI check, tap a mode:")
        lines += [f"{mark(mode == settings.ai_mode)} {AI_MODE_NAMES[mode]}: {AI_MODE_HINTS[mode]}"
                  for mode in AI_MODES]
    else:
        lines.append("🤖 The AI check needs AI_API_KEY and AI_MODEL in .env.")
    return "\n".join(lines)
