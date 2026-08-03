"""Deterministic exact and fuzzy lookup over normalized vector icons."""

from __future__ import annotations

from difflib import SequenceMatcher
from functools import lru_cache
from typing import Iterable

from app.icons.catalog import load_builtin_icons
from app.icons.models import VectorIcon
from app.icons.naming import normalize_icon_name


class CatalogRegistry:
    """An immutable in-memory index of a brand icon catalog."""

    def __init__(self, icons: Iterable[VectorIcon]) -> None:
        self._icons = tuple(sorted(icons, key=lambda icon: icon.key))
        self._by_key: dict[str, VectorIcon] = {}
        self._exact: dict[str, VectorIcon] = {}
        self._names: dict[str, set[str]] = {}
        candidates: dict[str, list[tuple[int, VectorIcon]]] = {}
        for icon in self._icons:
            if icon.key in self._by_key:
                raise ValueError(f"Duplicate icon key: {icon.key}")
            self._by_key[icon.key] = icon
            prioritized_names = (
                (0, icon.key),
                (1, icon.title),
                *((2, alias) for alias in icon.aliases),
            )
            normalized_names = {
                normalize_icon_name(name) for _, name in prioritized_names
            }
            for priority, name in prioritized_names:
                normalized = normalize_icon_name(name)
                candidates.setdefault(normalized, []).append((priority, icon))
            self._names[icon.key] = normalized_names

        for name, matches in candidates.items():
            best_priority = min(priority for priority, _ in matches)
            best = {
                icon.key: icon
                for priority, icon in matches
                if priority == best_priority
            }
            if len(best) == 1:
                self._exact[name] = next(iter(best.values()))

    def __len__(self) -> int:
        return len(self._icons)

    @property
    def icons(self) -> tuple[VectorIcon, ...]:
        """Return icons in stable key order for metadata and merged registries."""
        return self._icons

    def get(self, key: str) -> VectorIcon | None:
        """Return an icon by its canonical catalog key."""
        return self._by_key.get(key)

    def exact(self, query: str) -> VectorIcon | None:
        """Return an icon when a normalized key, title, or alias matches."""
        return self._exact.get(normalize_icon_name(query))

    def suggest(self, query: str, *, limit: int = 5) -> tuple[VectorIcon, ...]:
        """Return deterministically ranked close matches above a useful cutoff."""
        normalized_query = normalize_icon_name(query)
        if not normalized_query or limit <= 0:
            return ()
        scored: list[tuple[float, str, VectorIcon]] = []
        for icon in self._icons:
            score = max(
                SequenceMatcher(None, normalized_query, name).ratio()
                for name in self._names[icon.key]
            )
            if score >= 0.6:
                scored.append((score, icon.key, icon))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return tuple(item[2] for item in scored[:limit])


@lru_cache(maxsize=1)
def load_builtin_registry() -> CatalogRegistry:
    """Load and cache the brand catalog distributed with the application."""
    return CatalogRegistry(load_builtin_icons())


class CombinedRegistry:
    """A custom-first view over local and bundled icon registries."""

    def __init__(self, custom, builtin: CatalogRegistry) -> None:
        self._custom = custom
        self._builtin = builtin
        warnings = []
        from app.icons.custom import CustomIconDiagnostic

        for icon in custom.icons.values():
            if builtin.get(icon.key) is not None or builtin.exact(icon.title) is not None:
                warnings.append(
                    CustomIconDiagnostic(
                        icon.key,
                        icon.key,
                        "warning",
                        "custom icon overrides a bundled catalog match",
                    )
                )
        self.diagnostics = (*custom.diagnostics, *warnings)

    def get(self, key: str) -> VectorIcon | None:
        return self._custom.get(key) or self._builtin.get(key)

    def exact(self, query: str) -> VectorIcon | None:
        return self._custom.exact(query) or self._builtin.exact(query)

    def suggest(self, query: str, *, limit: int = 8) -> tuple[VectorIcon, ...]:
        merged: dict[str, VectorIcon] = {}
        for icon in self._custom.suggest(query, limit=limit):
            merged[icon.key] = icon
        for icon in self._builtin.suggest(query, limit=limit):
            merged.setdefault(icon.key, self._custom.get(icon.key) or icon)
        return tuple(merged.values())[:limit]

    def diagnostic_for(self, key: str):
        return self._custom.diagnostic_for(key)
