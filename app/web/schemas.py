"""Pydantic edge models for the web API.

Shape validation only — field presence and type. Every domain rule
(categories, styles, themes, formats, size bounds) lives in IconRequest and
app/utils/validation.py and must not be duplicated here.
"""

from __future__ import annotations

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    """Body of POST /api/generate. Defaults mirror the previous Flask route."""

    name: str = ""
    category: str = ""
    style: str = "minimal"
    theme: str = "blue"
    custom_color: str | None = None
    size: int = 256
    format: str = "both"
    icon: str = "auto"
    transparent_bg: bool = False
