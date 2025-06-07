"""Test the Reolink siren platform."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from reolink_aio.exceptions import InvalidParameterError, ReolinkError

from menuai.components.siren import (
    ATTR_DURATION,
    ATTR_VOLUME_LEVEL,
    DOMAIN as SIREN_DOMAIN,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNKNOWN,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError

from .conftest import TEST_NVR_NAME

from tests.common import MockConfigEntry


async def test_siren(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
) -> None:
    """Test siren entity."""
    with patch("menuai.components.reolink.PLATFORMS", [Platform.SIREN]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.SIREN}.{TEST_NVR_NAME}_siren"
    assert menuai.states.get(entity_id).state == STATE_UNKNOWN

    # test siren turn on
    await menuai.services.async_call(
        SIREN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    reolink_connect.set_volume.assert_not_called()
    reolink_connect.set_siren.assert_called_with(0, True, None)

    await menuai.services.async_call(
        SIREN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_VOLUME_LEVEL: 0.85, ATTR_DURATION: 2},
        blocking=True,
    )
    reolink_connect.set_volume.assert_called_with(0, volume=85)
    reolink_connect.set_siren.assert_called_with(0, True, 2)

    # test siren turn off
    await menuai.services.async_call(
        SIREN_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    reolink_connect.set_siren.assert_called_with(0, False, None)


@pytest.mark.parametrize("attr", ["set_volume", "set_siren"])
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            AsyncMock(side_effect=ReolinkError("Test error")),
            menuaiError,
        ),
        (
            AsyncMock(side_effect=InvalidParameterError("Test error")),
            ServiceValidationError,
        ),
    ],
)
async def test_siren_turn_on_errors(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
    attr: str,
    value: Any,
    expected: Any,
) -> None:
    """Test errors when calling siren turn on service."""
    with patch("menuai.components.reolink.PLATFORMS", [Platform.SIREN]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.SIREN}.{TEST_NVR_NAME}_siren"

    original = getattr(reolink_connect, attr)
    setattr(reolink_connect, attr, value)
    with pytest.raises(expected):
        await menuai.services.async_call(
            SIREN_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id, ATTR_VOLUME_LEVEL: 0.85, ATTR_DURATION: 2},
            blocking=True,
        )

    setattr(reolink_connect, attr, original)


async def test_siren_turn_off_errors(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
) -> None:
    """Test errors when calling siren turn off service."""
    with patch("menuai.components.reolink.PLATFORMS", [Platform.SIREN]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.SIREN}.{TEST_NVR_NAME}_siren"

    reolink_connect.set_siren.side_effect = ReolinkError("Test error")
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            SIREN_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

    reolink_connect.set_siren.reset_mock(side_effect=True)
