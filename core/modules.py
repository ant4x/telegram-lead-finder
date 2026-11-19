"""The bot's modules: "mentions" is the Shillometer, "leads" is the lead finder. MODULES in .env picks them."""

MODULES = ("mentions", "leads")
DEFAULT_MODULES = frozenset({"mentions"})


def parse_modules(names: list[str]) -> frozenset[str]:
    """
    The modules named in MODULES, in any case and with spaces around; the Shillometer alone when MODULES is
    missing or empty, so a bot set up before the lead finder runs as it did. An unknown name is an error.
    """
    chosen = frozenset(name.strip().lower() for name in names if name.strip())
    unknown = chosen - set(MODULES)
    if unknown:
        raise ValueError(f"Unknown modules in MODULES: {', '.join(sorted(unknown))}. Use {' and '.join(MODULES)}.")
    return chosen or DEFAULT_MODULES
