"""Test the Reolink number platform."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from reolink_aio.api import Chime
from reolink_aio.exceptions import InvalidParameterError, ReolinkError

from menuai.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError

from .conftest import TEST_NVR_NAME

from tests.common import MockConfigEntry


async def test_number(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
) -> None:
    """Test number entity with volume."""
    reolink_connect.volume.return_value = 80

    with patch("menuai.components.reolink.PLATFORMS", [Platform.NUMBER]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.NUMBER}.{TEST_NVR_NAME}_volume"

    assert menuai.states.get(entity_id).state == "80"

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 50},
        blocking=True,
    )
    reolink_connect.set_volume.assert_called_with(0, volume=50)

    reolink_connect.set_volume.side_effect = ReolinkError("Test error")
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 50},
            blocking=True,
        )

    reolink_connect.set_volume.side_effect = InvalidParameterError("Test error")
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 50},
            blocking=True,
        )

    reolink_connect.set_volume.reset_mock(side_effect=True)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_smart_ai_number(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
) -> None:
    """Test number entity with smart ai sensitivity."""
    reolink_connect.baichuan.smart_ai_sensitivity.return_value = 80

    with patch("menuai.components.reolink.PLATFORMS", [Platform.NUMBER]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.NUMBER}.{TEST_NVR_NAME}_AI_crossline_zone1_sensitivity"

    assert menuai.states.get(entity_id).state == "80"

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 50},
        blocking=True,
    )
    reolink_connect.baichuan.set_smart_ai.assert_called_with(
        0, "crossline", 0, sensitivity=50
    )

    reolink_connect.baichuan.set_smart_ai.side_effect = InvalidParameterError(
        "Test error"
    )
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 50},
            blocking=True,
        )

    reolink_connect.baichuan.set_smart_ai.reset_mock(side_effect=True)


async def test_host_number(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
) -> None:
    """Test number entity with volume."""
    reolink_connect.alarm_volume = 85

    with patch("menuai.components.reolink.PLATFORMS", [Platform.NUMBER]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.NUMBER}.{TEST_NVR_NAME}_alarm_volume"

    assert menuai.states.get(entity_id).state == "85"

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 45},
        blocking=True,
    )
    reolink_connect.set_hub_audio.assert_called_with(alarm_volume=45)

    reolink_connect.set_hub_audio.side_effect = ReolinkError("Test error")
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 45},
            blocking=True,
        )

    reolink_connect.set_hub_audio.side_effect = InvalidParameterError("Test error")
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 45},
            blocking=True,
        )


async def test_chime_number(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
    test_chime: Chime,
) -> None:
    """Test number entity of a chime with chime volume."""
    test_chime.volume = 3

    with patch("menuai.components.reolink.PLATFORMS", [Platform.NUMBER]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.NUMBER}.test_chime_volume"

    assert menuai.states.get(entity_id).state == "3"

    test_chime.set_option = AsyncMock()
    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 2},
        blocking=True,
    )
    test_chime.set_option.assert_called_with(volume=2)

    test_chime.set_option.side_effect = ReolinkError("Test error")
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 1},
            blocking=True,
        )

    test_chime.set_option.side_effect = InvalidParameterError("Test error")
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 1},
            blocking=True,
        )

    test_chime.set_option.reset_mock(side_effect=True)
