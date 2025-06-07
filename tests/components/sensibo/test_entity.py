"""The test for the sensibo entity."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.climate import (
    ATTR_FAN_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_FAN_MODE,
)
from menuai.components.sensibo.const import SENSIBO_ERRORS
from menuai.config_entries import ConfigEntry
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import device_registry as dr


async def test_device(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    load_int: ConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Sensibo device."""

    state1 = menuai.states.get("climate.hallway")
    assert state1

    assert (
        dr.async_entries_for_config_entry(device_registry, load_int.entry_id)
        == snapshot
    )


@pytest.mark.parametrize("p_error", SENSIBO_ERRORS)
async def test_entity_failed_service_calls(
    menuai: menuai,
    p_error: Exception,
    load_int: ConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the Sensibo send command with error."""

    state = menuai.states.get("climate.hallway")
    assert state

    mock_client.async_set_ac_state_property.return_value = {
        "result": {"status": "Success"}
    }

    await menuai.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_FAN_MODE,
        {ATTR_ENTITY_ID: state.entity_id, ATTR_FAN_MODE: "low"},
        blocking=True,
    )

    state = menuai.states.get("climate.hallway")
    assert state.attributes["fan_mode"] == "low"

    mock_client.async_set_ac_state_property.side_effect = p_error

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_FAN_MODE,
            {ATTR_ENTITY_ID: state.entity_id, ATTR_FAN_MODE: "low"},
            blocking=True,
        )

    state = menuai.states.get("climate.hallway")
    assert state.attributes["fan_mode"] == "low"
