"""Tests for the switch module."""

from unittest.mock import AsyncMock, MagicMock, patch

from eheimdigital.types import EheimDeviceType
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import init_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.usefixtures("classic_vario_mock")
async def test_setup_classic_vario(
    menuai: menuai,
    eheimdigital_hub_mock: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test switch platform setup for the filter."""
    mock_config_entry.add_to_menuai(menuai)

    with (
        patch("menuai.components.eheimdigital.PLATFORMS", [Platform.SWITCH]),
        patch(
            "menuai.components.eheimdigital.coordinator.asyncio.Event",
            new=AsyncMock,
        ),
    ):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)

    await eheimdigital_hub_mock.call_args.kwargs["device_found_callback"](
        "00:00:00:00:00:03", EheimDeviceType.VERSION_EHEIM_CLASSIC_VARIO
    )
    await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("service", "active"), [(SERVICE_TURN_OFF, False), (SERVICE_TURN_ON, True)]
)
async def test_turn_on_off(
    menuai: menuai,
    eheimdigital_hub_mock: MagicMock,
    mock_config_entry: MockConfigEntry,
    classic_vario_mock: MagicMock,
    service: str,
    active: bool,
) -> None:
    """Test turning on/off the switch."""
    await init_integration(menuai, mock_config_entry)

    await eheimdigital_hub_mock.call_args.kwargs["device_found_callback"](
        "00:00:00:00:00:03", EheimDeviceType.VERSION_EHEIM_CLASSIC_VARIO
    )
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        service,
        {ATTR_ENTITY_ID: "switch.mock_classicvario"},
        blocking=True,
    )

    calls = [
        call for call in classic_vario_mock.hub.mock_calls if call[0] == "send_packet"
    ]
    assert len(calls) == 1
    assert calls[0][1][0].get("filterActive") == int(active)


@pytest.mark.usefixtures("classic_vario_mock")
@pytest.mark.parametrize(
    ("device_name", "entity_list"),
    [
        (
            "classic_vario_mock",
            [
                (
                    "switch.mock_classicvario",
                    "classic_vario_data",
                    "filterActive",
                    1,
                    "on",
                ),
                (
                    "switch.mock_classicvario",
                    "classic_vario_data",
                    "filterActive",
                    0,
                    "off",
                ),
            ],
        ),
    ],
)
async def test_state_update(
    menuai: menuai,
    eheimdigital_hub_mock: MagicMock,
    mock_config_entry: MockConfigEntry,
    device_name: str,
    entity_list: list[tuple[str, str, str, float, float]],
    request: pytest.FixtureRequest,
) -> None:
    """Test the switch state update."""
    device: MagicMock = request.getfixturevalue(device_name)
    await init_integration(menuai, mock_config_entry)

    await eheimdigital_hub_mock.call_args.kwargs["device_found_callback"](
        device.mac_address, device.device_type
    )

    await menuai.async_block_till_done()

    for item in entity_list:
        getattr(device, item[1])[item[2]] = item[3]
        await eheimdigital_hub_mock.call_args.kwargs["receive_callback"]()
        assert (state := menuai.states.get(item[0]))
        assert state.state == str(item[4])
