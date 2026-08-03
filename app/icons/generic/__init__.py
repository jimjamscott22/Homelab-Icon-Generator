"""Registry for all built-in procedural fallback icons."""

from app.icons.generic.devices import DEVICE_ICONS
from app.icons.generic.infrastructure import INFRASTRUCTURE_ICONS
from app.icons.generic.services import SERVICE_ICONS
from app.icons.models import VectorIcon

GENERIC_ICONS: dict[str, VectorIcon] = {
    **INFRASTRUCTURE_ICONS,
    **DEVICE_ICONS,
    **SERVICE_ICONS,
}


def get_generic_icon(category: str) -> VectorIcon:
    """Return a generic icon or raise a clear category error."""
    try:
        return GENERIC_ICONS[category]
    except KeyError as exc:
        raise ValueError(f"Unknown generic category '{category}'") from exc


__all__ = ["GENERIC_ICONS", "get_generic_icon"]
