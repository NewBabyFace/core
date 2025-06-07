"""Test the Reolink services."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from reolink_aio.api import Chime
from reolink_aio.exceptions import InvalidParameterError, ReolinkError

from menuai.components.reolink.const import DOMAIN
from menuai.components.reolink.services import ATTR_RINGTONE
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_DEVICE_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def test_play_chime_service_entity(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
    test_chime: Chime,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test chime play service."""
    with patch("menuai.components.reolink.PLATFORMS", [Platform.SELECT]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.SELECT}.test_chime_visitor_ringtone"
    entity = entity_registry.async_get(entity_id)
    assert entity is not None
    device_id = entity.device_id

    # Test chime play service with device
    test_chime.play = AsyncMock()
    await menuai.services.async_call(
        DOMAIN,
        "play_chime",
        {ATTR_DEVICE_ID: [device_id], ATTR_RINGTONE: "attraction"},
        blocking=True,
    )
    test_chime.play.assert_called_once()

    # Test errors
    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            DOMAIN,
            "play_chime",
            {ATTR_DEVICE_ID: ["invalid_id"], ATTR_RINGTONE: "attraction"},
            blocking=True,
        )

    test_chime.play = AsyncMock(side_effect=ReolinkError("Test error"))
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            DOMAIN,
            "play_chime",
            {ATTR_DEVICE_ID: [device_id], ATTR_RINGTONE: "attraction"},
            blocking=True,
        )

    test_chime.play = AsyncMock(side_effect=InvalidParameterError("Test error"))
    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            DOMAIN,
            "play_chime",
            {ATTR_DEVICE_ID: [device_id], ATTR_RINGTONE: "attraction"},
            blocking=True,
        )

    reolink_connect.chime.return_value = None
    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            DOMAIN,
            "play_chime",
            {ATTR_DEVICE_ID: [device_id], ATTR_RINGTONE: "attraction"},
            blocking=True,
        )


async def test_play_chime_service_unloaded(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
    test_chime: Chime,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test chime play service when config entry is unloaded."""
    with patch("menuai.components.reolink.PLATFORMS", [Platform.SELECT]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.SELECT}.test_chime_visitor_ringtone"
    entity = entity_registry.async_get(entity_id)
    assert entity is not None
    device_id = entity.device_id

    # Unload the config entry
    assert await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED

    # Test chime play service
    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            DOMAIN,
            "play_chime",
            {ATTR_DEVICE_ID: [device_id], ATTR_RINGTONE: "attraction"},
            blocking=True,
        )
