"""Tests for the Abode cover device."""

from unittest.mock import patch

from menuai.components.abode import ATTR_DEVICE_ID
from menuai.components.cover import DOMAIN as COVER_DOMAIN, CoverState
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import setup_platform

DEVICE_ID = "cover.garage_door"


async def test_entity_registry(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Tests that the devices are registered in the entity registry."""
    await setup_platform(menuai, COVER_DOMAIN)

    entry = entity_registry.async_get(DEVICE_ID)
    assert entry.unique_id == "61cbz3b542d2o33ed2fz02721bda3324"


async def test_attributes(menuai: menuai) -> None:
    """Test the cover attributes are correct."""
    await setup_platform(menuai, COVER_DOMAIN)

    state = menuai.states.get(DEVICE_ID)
    assert state.state == CoverState.CLOSED
    assert state.attributes.get(ATTR_DEVICE_ID) == "ZW:00000007"
    assert not state.attributes.get("battery_low")
    assert not state.attributes.get("no_response")
    assert state.attributes.get("device_type") == "Secure Barrier"
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Garage Door"


async def test_open(menuai: menuai) -> None:
    """Test the cover can be opened."""
    await setup_platform(menuai, COVER_DOMAIN)

    with patch("jaraco.abode.devices.cover.Cover.open_cover") as mock_open:
        await menuai.services.async_call(
            COVER_DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: DEVICE_ID}, blocking=True
        )
        await menuai.async_block_till_done()
        mock_open.assert_called_once()


async def test_close(menuai: menuai) -> None:
    """Test the cover can be closed."""
    await setup_platform(menuai, COVER_DOMAIN)

    with patch("jaraco.abode.devices.cover.Cover.close_cover") as mock_close:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: DEVICE_ID},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_close.assert_called_once()
