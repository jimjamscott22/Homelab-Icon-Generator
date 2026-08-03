"""Conservative, offline icon selection and suggestion behavior."""

from __future__ import annotations

from functools import lru_cache

from app.icons.generic import get_generic_icon
from app.icons.models import IconResolution, VectorIcon
from app.icons.naming import normalize_icon_name
from app.icons.registry import CatalogRegistry, CombinedRegistry, load_builtin_registry
from app.models.icon_request import IconRequest


_DEPLOYMENT_SUFFIXES = frozenset(
    {"app", "service", "server", "instance", "container", "vm"}
)


def strip_deployment_suffix(value: str) -> str:
    """Remove only controlled trailing deployment terms from a normalized name."""
    words = normalize_icon_name(value).split()
    while len(words) > 1 and words[-1] in _DEPLOYMENT_SUFFIXES:
        words.pop()
    return " ".join(words)


class IconResolver:
    """Resolve exact brand matches while keeping fuzzy search advisory-only."""

    def __init__(self, catalog: CatalogRegistry | CombinedRegistry) -> None:
        self._catalog = catalog

    def resolve(self, request: IconRequest) -> IconResolution:
        query = normalize_icon_name(request.name)
        selection = request.icon.strip()
        if selection == "generic":
            return self._generic(request, query, used_fallback=False)
        if selection != "auto":
            icon = self._catalog.get(selection)
            if icon is None:
                diagnostic_for = getattr(self._catalog, "diagnostic_for", None)
                diagnostic = diagnostic_for(selection) if diagnostic_for else None
                if diagnostic is not None:
                    raise ValueError(
                        f"Custom icon '{selection}' is unavailable: {diagnostic.message}"
                    )
                suggestions = self.suggest(selection, limit=3)
                hint = ""
                if suggestions:
                    hint = ". Suggestions: " + ", ".join(
                        icon.key for icon in suggestions
                    )
                raise ValueError(f"Unknown explicit icon '{selection}'{hint}")
            return IconResolution(icon, "explicit", query, used_fallback=False)

        icon = self._catalog.exact(query)
        if icon is not None:
            return self._matched(icon, query, normalized=False)

        stripped = strip_deployment_suffix(query)
        if stripped != query:
            icon = self._catalog.exact(stripped)
            if icon is not None:
                return self._matched(icon, query, normalized=True)
        return self._generic(request, query, used_fallback=True)

    def suggest(self, query: str, *, limit: int = 8) -> tuple[VectorIcon, ...]:
        """Return close manual choices without changing automatic selection."""
        return self._catalog.suggest(query, limit=limit)

    @staticmethod
    def _matched(
        icon: VectorIcon, query: str, *, normalized: bool
    ) -> IconResolution:
        if normalized:
            method = "normalized"
        elif icon.source == "custom":
            method = "custom"
        else:
            method = "catalog"
        return IconResolution(icon, method, query, used_fallback=False)

    @staticmethod
    def _generic(
        request: IconRequest, query: str, *, used_fallback: bool
    ) -> IconResolution:
        return IconResolution(
            get_generic_icon(request.category),
            "generic",
            query,
            used_fallback=used_fallback,
        )


@lru_cache(maxsize=1)
def get_default_resolver() -> IconResolver:
    """Return the process-wide resolver backed by bundled offline data."""
    return build_resolver()


def build_resolver(icon_dir: str | None = None) -> IconResolver:
    """Build a resolver using explicit, environment, or working-directory custom data."""
    from app.icons.custom import load_custom_registry, resolve_custom_icon_dir

    custom = load_custom_registry(resolve_custom_icon_dir(icon_dir))
    return IconResolver(CombinedRegistry(custom, load_builtin_registry()))


__all__ = [
    "IconResolver",
    "build_resolver",
    "get_default_resolver",
    "normalize_icon_name",
    "strip_deployment_suffix",
]
