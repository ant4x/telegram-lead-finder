"""Who may use the lead finder. A category of users other than admins, if one comes, is checked here too."""


def can_use_leads(user_id: int, admins: frozenset[int]) -> bool:
    """Admins only, for now."""
    return user_id in admins
