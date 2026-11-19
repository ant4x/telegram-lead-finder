"""
The rules that find leads: a message is a lead when it names a word of a niche and a phrase of one of the kinds,
and has none of the exclusions. They need no database and no network, so they run on every message first.
"""
import hashlib
import re
from dataclasses import dataclass

from core.leads.phrases import EXCLUDE, HASHTAG_KINDS, PROBLEM, REQUEST, VACANCY
from core.text import mentions

KINDS = ("request", "vacancy", "problem")  # in priority order: a message with phrases of two kinds gets the first
PHRASES = {"request": REQUEST, "vacancy": VACANCY, "problem": PROBLEM}
LINKS = re.compile(r"https?://\S+|t\.me/\S+|www\.\S+")


@dataclass(frozen=True)
class Niche:
    id: int
    owner_id: int
    name: str
    words: tuple[str, ...]


def _names_any(text: str, phrases) -> bool:
    return any(mentions(text, phrase) for phrase in phrases)


def lead_kind(text: str) -> str | None:
    """The kind of lead the text asks for: an exclusion rules it out, a job board hashtag decides, then phrases."""
    if _names_any(text, EXCLUDE):
        return None
    for kind in KINDS:
        if _names_any(text, [tag for tag, tag_kind in HASHTAG_KINDS.items() if tag_kind == kind]):
            return kind
    for kind in KINDS:
        if _names_any(text, PHRASES[kind]):
            return kind
    return None


def matching_niches(text: str, niches: list[Niche]) -> list[Niche]:
    """The niches whose words the text names."""
    return [niche for niche in niches if _names_any(text, niche.words)]


def text_hash(text: str) -> str:
    """A fingerprint of the text for spotting the same message sent to several chats: case, links and spaces aside."""
    plain = " ".join(LINKS.sub(" ", text.lower()).split())
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()
