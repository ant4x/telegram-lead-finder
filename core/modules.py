"""The bot's modules: "mentions" is the Shillometer, "leads" is the lead finder. MODULES in .env picks them."""

MODULES = ("mentions", "leads")


def parse_modules(names: list[str]) -> frozenset[str]:
    """The modules named in MODULES, in any case and with spaces around. An unknown name or none at all is an error."""
    chosen = frozenset(name.strip().lower() for name in names if name.strip())
    unknown = chosen - set(MODULES)
    if unknown:
        raise ValueError(f"Unknown modules in MODULES: {', '.join(sorted(unknown))}. Use {' and '.join(MODULES)}.")
    if not chosen:
        raise ValueError(f"MODULES is empty. Use {' and '.join(MODULES)}.")
    return chosen
