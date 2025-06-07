"""Tests for the select module."""

from unittest.mock import AsyncMock, MagicMock, patch

from eheimdigital.types import FilterMode
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .conftest import init_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.usefixtures("classic_vario_mock")
async def test_setup(
    menuai: menuai,
    eheimdigital_hub_mock: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test select platform setup."""
    mock_config_entry.add_to_menuai(menuai)

    with (
        patch("menuai.components.eheimdigital.PLATFORMS", [Platform.SELECT]),
        patch(
            "menuai.components.eheimdigital.coordinator.asyncio.Event",
            new=AsyncMock,
        ),
    ):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)

    for device in eheimdigital_hub_mock.return_value.devices:
        await eheimdigital_hub_mock.call_args.kwargs["device_found_callback"](
            device, eheimdigital_hub_mock.return_value.devices[device].device_type
        )
        await menuai.async_block_till_done()

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.usefixtures("classic_vario_mock")
@pytest.mark.parametrize(
    ("device_name", "entity_list"),
    [
        (
            "classic_vario_mock",
            [
                (
                    "select.mock_classicvario_filter_mode",
                    "manual",
                    "pumpMode",
                    int(FilterMode.MANUAL),
                ),
            ],
        ),
    ],
)
async def test_set_value(
    menuai: menuai,
    eheimdigital_hub_mock: MagicMock,
    mock_config_entry: MockConfigEntry,
    device_name: str,
    entity_list: list[tuple[str, str, str, int]],
    request: pytest.FixtureRequest,
) -> None:
    """Test setting a value."""
    device: MagicMock = request.getfixturevalue(device_name)
    await init_integration(menuai, mock_config_entry)

    await eheimdigital_hub_mock.call_args.kwargs["device_found_callback"](
        device.mac_address, device.device_type
    )

    await menuai.async_block_till_done()

    for item in entity_list:
        await menuai.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: item[0], ATTR_OPTION: item[1]},
            blocking=True,
        )
        calls = [call for call in device.hub.mock_calls if call[0] == "send_packet"]
        assert calls[-1][1][0][item[2]] == item[3]


@pytest.mark.usefixtures("classic_vario_mock", "heater_mock")
@pytest.mark.parametrize(
    ("device_name", "entity_list"),
    [
        (
            "classic_vario_mock",
            [
                (
                    "select.mock_classicvario_filter_mode",
                    "classic_vario_data",
                    "pumpMode",
                    int(FilterMode.BIO),
                    "bio",
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
    entity_list: list[tuple[str, str, str, int, str]],
    request: pytest.FixtureRequest,
) -> None:
    """Test state updates."""
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
        assert state.state == item[4]
