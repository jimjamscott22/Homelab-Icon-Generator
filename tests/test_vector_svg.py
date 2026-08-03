"""Tests for normalized vector icons and deterministic SVG serialization."""

import pytest

from app.icons.models import IconResolution, VectorIcon, VectorNode
from app.icons.svg import serialize_nodes


@pytest.fixture
def sample_icon() -> VectorIcon:
    return VectorIcon(
        key="test",
        title="Test",
        source="fixture",
        view_box=(0, 0, 24, 24),
        nodes=(
            VectorNode(
                "path",
                {"d": "M0 0h24v24z", "fill-rule": "evenodd"},
            ),
        ),
    )


def test_serialize_path_uses_requested_color_and_stable_attribute_order(
    sample_icon: VectorIcon,
) -> None:
    """A wrong paint color or unstable attribute ordering must fail."""
    assert serialize_nodes(sample_icon.nodes, "#4fc3f7") == (
        '<path d="M0 0h24v24z" fill="#4fc3f7" fill-rule="evenodd"/>'
    )


def test_serialize_group_recolors_current_color_and_escapes_values() -> None:
    """A serializer that leaks XML or leaves currentColor unresolved must fail."""
    nodes = (
        VectorNode(
            "g",
            {"aria-label": 'A&B "icon"'},
            (
                VectorNode(
                    "line",
                    {"x1": 0, "y1": 1, "x2": 2, "y2": 3, "stroke": "currentColor"},
                ),
            ),
        ),
    )

    assert serialize_nodes(nodes, "#39ff14") == (
        '<g aria-label="A&amp;B &quot;icon&quot;">'
        '<line stroke="#39ff14" x1="0" x2="2" y1="1" y2="3"/>'
        "</g>"
    )


def test_serialize_rejects_unsupported_elements() -> None:
    """Adding active SVG tags to the vector model must remain impossible."""
    with pytest.raises(ValueError, match="Unsupported vector element"):
        VectorNode("script", {})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        ("generic", True),
        ("catalog", False),
        ("custom", False),
        ("explicit", False),
        ("normalized", False),
    ],
)
def test_resolution_derives_initials_policy(
    sample_icon: VectorIcon,
    method: str,
    expected: bool,
) -> None:
    """Only a generic resolution may request initials."""
    result = IconResolution(
        icon=sample_icon,
        match_method=method,  # type: ignore[arg-type]
        query="test",
        used_fallback=method == "generic",
    )

    assert result.show_initials is expected
