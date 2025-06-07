"""Tests for the devolo Home Network buttons."""

from unittest.mock import AsyncMock

from devolo_plc_api.exceptions.device import DevicePasswordProtected, DeviceUnavailable
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as PLATFORM, SERVICE_PRESS
from menuai.components.devolo_home_network.const import DOMAIN
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import configure_integration
from .mock import MockDevice


@pytest.mark.usefixtures("mock_device")
async def test_button_setup(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test default setup of the button component."""
    entry = configure_integration(menuai)
    device_name = entry.title.replace(" ", "_").lower()
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert not entity_registry.async_get(
        f"{PLATFORM}.{device_name}_identify_device_with_a_blinking_led"
    ).disabled
    assert not entity_registry.async_get(
        f"{PLATFORM}.{device_name}_start_plc_pairing"
    ).disabled
    assert not entity_registry.async_get(
        f"{PLATFORM}.{device_name}_restart_device"
    ).disabled
    assert not entity_registry.async_get(f"{PLATFORM}.{device_name}_start_wps").disabled


@pytest.mark.parametrize(
    ("name", "api_name", "trigger_method"),
    [
        (
            "identify_device_with_a_blinking_led",
            "plcnet",
            "async_identify_device_start",
        ),
        (
            "start_plc_pairing",
            "plcnet",
            "async_pair_device",
        ),
        (
            "restart_device",
            "device",
            "async_restart",
        ),
        (
            "start_wps",
            "device",
            "async_start_wps",
        ),
    ],
)
@pytest.mark.freeze_time("2023-01-13 12:00:00+00:00")
async def test_button(
    menuai: menuai,
    mock_device: MockDevice,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    name: str,
    api_name: str,
    trigger_method: str,
) -> None:
    """Test a button."""
    entry = configure_integration(menuai)
    device_name = entry.title.replace(" ", "_").lower()
    state_key = f"{PLATFORM}.{device_name}_{name}"
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get(state_key) == snapshot
    assert entity_registry.async_get(state_key) == snapshot

    # Emulate button press
    await menuai.services.async_call(
        PLATFORM,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: state_key},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(state_key)
    assert state.state == "2023-01-13T12:00:00+00:00"
    api = getattr(mock_device, api_name)
    assert getattr(api, trigger_method).call_count == 1

    # Emulate device failure
    setattr(api, trigger_method, AsyncMock())
    getattr(api, trigger_method).side_effect = DeviceUnavailable
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            PLATFORM,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: state_key},
            blocking=True,
        )


async def test_auth_failed(menuai: menuai, mock_device: MockDevice) -> None:
    """Test setting unautherized triggers the reauth flow."""
    entry = configure_integration(menuai)
    device_name = entry.title.replace(" ", "_").lower()
    state_key = f"{PLATFORM}.{device_name}_start_wps"

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    mock_device.device.async_start_wps.side_effect = DevicePasswordProtected

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            PLATFORM,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: state_key},
            blocking=True,
        )

    await menuai.async_block_till_done()
    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    flow = flows[0]
    assert flow["step_id"] == "reauth_confirm"
    assert flow["handler"] == DOMAIN
    assert "context" in flow
    assert flow["context"]["source"] == SOURCE_REAUTH
    assert flow["context"]["entry_id"] == entry.entry_id
