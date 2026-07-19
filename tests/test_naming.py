"""Tests for initials generation."""

import pytest

from app.utils.naming import generate_initials


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Nextcloud", "N"),
        ("Pi Hole", "PH"),
        ("Raspberry Pi Server", "RPS"),
        ("home assistant core service", "HAC"),  # capped at three words
        ("  spaced   out  ", "SO"),
    ],
)
def test_generate_initials(name, expected):
    assert generate_initials(name) == expected


def test_empty_name_raises():
    with pytest.raises(ValueError):
        generate_initials("   ")
