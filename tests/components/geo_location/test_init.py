"""The tests for the geolocation component."""

import pytest

from menuai.components import geo_location
from menuai.components.geo_location import GeolocationEvent
from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_setup_component(menuai: menuai) -> None:
    """Simple test setup of component."""
    result = await async_setup_component(menuai, geo_location.DOMAIN, {})
    assert result


async def test_event(menuai: menuai) -> None:
    """Simple test of the geolocation event class."""
    entity = GeolocationEvent()

    assert entity.state is None
    assert entity.distance is None
    assert entity.latitude is None
    assert entity.longitude is None
    with pytest.raises(AttributeError):
        assert entity.source is None
