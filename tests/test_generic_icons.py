"""Coverage for single-source generic vector definitions."""

import pytest

from app.icons.generic import get_generic_icon
from app.utils.validation import VALID_CATEGORIES


@pytest.mark.parametrize("category", sorted(VALID_CATEGORIES))
def test_every_category_has_one_nonempty_vector_definition(category: str) -> None:
    """Removing or mis-keying a generic fallback must fail."""
    icon = get_generic_icon(category)

    assert icon.key == category
    assert icon.source == "generic"
    assert icon.nodes


def test_unknown_generic_category_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown generic category"):
        get_generic_icon("missing-category")
