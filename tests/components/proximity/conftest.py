"""Config test for proximity."""

import pytest

from menuai.core import menuai


@pytest.fixture(autouse=True)
def config_zones(menuai: menuai):
    """Set up zones for test."""
    menuai.config.components.add("zone")
    menuai.states.async_set(
        "zone.home",
        "zoning",
        {"name": "Home", "latitude": 2.1, "longitude": 1.1, "radius": 10},
    )
    menuai.states.async_set(
        "zone.work",
        "zoning",
        {"name": "Work", "latitude": 2.3, "longitude": 1.3, "radius": 10},
    )
