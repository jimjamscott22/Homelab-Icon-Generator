"""Utilities for deriving display names and initials from icon names."""


def generate_initials(name: str) -> str:
    """Return up to three uppercase initials derived from a service name.

    - 1 word  -> first letter
    - 2 words -> first letter of each word
    - 3+ words -> first letter of the first three words

    Examples:
        "Nextcloud"          -> "N"
        "Pi Hole"            -> "PH"
        "Raspberry Pi Server"-> "RPS"
    """
    words = name.split()
    if not words:
        raise ValueError("name must not be empty")
    return "".join(w[0].upper() for w in words[:3])
