"""Tests for Kaleidescape sensor platform."""

from unittest.mock import MagicMock

from kaleidescape import const as kaleidescape_const
import pytest

from menuai.const import ATTR_FRIENDLY_NAME
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import MOCK_SERIAL

ENTITY_ID = f"sensor.kaleidescape_device_{MOCK_SERIAL}"
FRIENDLY_NAME = f"Kaleidescape Device {MOCK_SERIAL}"


@pytest.mark.usefixtures("mock_integration")
async def test_sensors(
    menuai: menuai, entity_registry: er.EntityRegistry, mock_device: MagicMock
) -> None:
    """Test sensors."""
    entity = menuai.states.get(f"{ENTITY_ID}_media_location")
    entry = entity_registry.async_get(f"{ENTITY_ID}_media_location")
    assert entity
    assert entity.state == "none"
    assert (
        entity.attributes.get(ATTR_FRIENDLY_NAME) == f"{FRIENDLY_NAME} Media location"
    )
    assert entry
    assert entry.unique_id == f"{MOCK_SERIAL}-media_location"

    entity = menuai.states.get(f"{ENTITY_ID}_play_status")
    entry = entity_registry.async_get(f"{ENTITY_ID}_play_status")
    assert entity
    assert entity.state == "none"
    assert entity.attributes.get(ATTR_FRIENDLY_NAME) == f"{FRIENDLY_NAME} Play status"
    assert entry
    assert entry.unique_id == f"{MOCK_SERIAL}-play_status"

    mock_device.movie.play_status = kaleidescape_const.PLAY_STATUS_PLAYING
    mock_device.dispatcher.send(kaleidescape_const.PLAY_STATUS)
    await menuai.async_block_till_done()
    entity = menuai.states.get(f"{ENTITY_ID}_play_status")
    assert entity is not None
    assert entity.state == "playing"
