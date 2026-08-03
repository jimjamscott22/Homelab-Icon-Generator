"""Canonical naming rules shared by icon registries and resolvers."""

from __future__ import annotations

import re
import unicodedata


_SEPARATORS = re.compile(r"[^\w]+", re.UNICODE)


def normalize_icon_name(value: str) -> str:
    """Normalize a human-entered icon name without destroying word boundaries."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(_SEPARATORS.sub(" ", normalized).split())
