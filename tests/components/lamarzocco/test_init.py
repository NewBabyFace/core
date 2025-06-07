"""Test initialization of lamarzocco."""

from unittest.mock import AsyncMock, MagicMock, patch

from pylamarzocco.const import FirmwareType, ModelName
from pylamarzocco.exceptions import AuthFail, RequestNotSuccessful
from pylamarzocco.models import WebSocketDetails
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.lamarzocco.config_flow import CONF_MACHINE
from menuai.components.lamarzocco.const import DOMAIN
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.const import (
    CONF_ADDRESS,
    CONF_HOST,
    CONF_MAC,
    CONF_MODEL,
    CONF_NAME,
    CONF_TOKEN,
    EVENT_menuai_STOP,
)
from menuai.core import menuai
from menuai.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)

from . import USER_INPUT, async_init_integration, get_bluetooth_service_info

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test loading and unloading the integration."""
    await async_init_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_config_entry_not_ready(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_lamarzocco: MagicMock,
) -> None:
    """Test the La Marzocco configuration entry not ready."""
    mock_lamarzocco.websocket.connected = False
    mock_lamarzocco.get_dashboard.side_effect = RequestNotSuccessful("")

    await async_init_integration(menuai, mock_config_entry)

    assert len(mock_lamarzocco.get_dashboard.mock_calls) == 1
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize(
    ("side_effect", "expected_state"),
    [
        (AuthFail(""), ConfigEntryState.SETUP_ERROR),
        (RequestNotSuccessful(""), ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_get_settings_errors(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_cloud_client: MagicMock,
    side_effect: Exception,
    expected_state: ConfigEntryState,
) -> None:
    """Test error during initial settings get."""
    mock_cloud_client.get_thing_settings.side_effect = side_effect

    await async_init_integration(menuai, mock_config_entry)

    assert len(mock_cloud_client.get_thing_settings.mock_calls) == 1
    assert mock_config_entry.state is expected_state


async def test_invalid_auth(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_lamarzocco: MagicMock,
) -> None:
    """Test auth error during setup."""
    mock_lamarzocco.websocket.connected = False
    mock_lamarzocco.get_dashboard.side_effect = AuthFail("")
    await async_init_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    assert len(mock_lamarzocco.get_dashboard.mock_calls) == 1

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    flow = flows[0]
    assert flow.get("step_id") == "reauth_confirm"
    assert flow.get("handler") == DOMAIN

    assert "context" in flow
    assert flow["context"].get("source") == SOURCE_REAUTH
    assert flow["context"].get("entry_id") == mock_config_entry.entry_id


async def test_v1_migration_fails(
    menuai: menuai,
    mock_lamarzocco: MagicMock,
) -> None:
    """Test v1 -> v2 Migration."""
    entry_v1 = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id=mock_lamarzocco.serial_number,
        data={},
    )

    entry_v1.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry_v1.entry_id)
    await menuai.async_block_till_done()

    assert entry_v1.state is ConfigEntryState.MIGRATION_ERROR


async def test_v2_migration(
    menuai: menuai,
    mock_lamarzocco: MagicMock,
) -> None:
    """Test v2 -> v3 Migration."""

    entry_v2 = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=mock_lamarzocco.serial_number,
        data={
            **USER_INPUT,
            CONF_HOST: "192.168.1.24",
            CONF_NAME: "La Marzocco",
            CONF_MODEL: ModelName.GS3_MP.value,
            CONF_MAC: "aa:bb:cc:dd:ee:ff",
        },
    )
    entry_v2.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry_v2.entry_id)
    assert entry_v2.state is ConfigEntryState.LOADED
    assert entry_v2.version == 3
    assert dict(entry_v2.data) == {
        **USER_INPUT,
        CONF_MAC: "aa:bb:cc:dd:ee:ff",
        CONF_TOKEN: None,
    }


async def test_migration_errors(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_cloud_client: MagicMock,
    mock_lamarzocco: MagicMock,
) -> None:
    """Test errors during migration."""

    mock_cloud_client.list_things.side_effect = RequestNotSuccessful("Error")

    entry_v2 = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=mock_lamarzocco.serial_number,
        data={
            **USER_INPUT,
            CONF_MACHINE: mock_lamarzocco.serial_number,
        },
    )
    entry_v2.add_to_menuai(menuai)

    assert not await menuai.config_entries.async_setup(entry_v2.entry_id)
    assert entry_v2.state is ConfigEntryState.MIGRATION_ERROR


async def test_config_flow_entry_migration_downgrade(
    menuai: menuai,
) -> None:
    """Test that config entry fails setup if the version is from the future."""
    entry = MockConfigEntry(domain=DOMAIN, version=4)
    entry.add_to_menuai(menuai)

    assert not await menuai.config_entries.async_setup(entry.entry_id)


async def test_bluetooth_is_set_from_discovery(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_lamarzocco: MagicMock,
    mock_cloud_client: MagicMock,
) -> None:
    """Check we can fill a device from discovery info."""

    service_info = get_bluetooth_service_info(
        ModelName.GS3_MP, mock_lamarzocco.serial_number
    )
    mock_cloud_client.get_thing_settings.return_value.ble_auth_token = "token"
    with (
        patch(
            "menuai.components.lamarzocco.async_discovered_service_info",
            return_value=[service_info],
        ) as discovery,
        patch(
            "menuai.components.lamarzocco.LaMarzoccoMachine"
        ) as mock_machine_class,
    ):
        mock_machine_class.return_value = mock_lamarzocco
        await async_init_integration(menuai, mock_config_entry)
    discovery.assert_called_once()
    assert mock_machine_class.call_count == 1
    _, kwargs = mock_machine_class.call_args
    assert kwargs["bluetooth_client"] is not None

    assert mock_config_entry.data[CONF_MAC] == service_info.address
    assert mock_config_entry.data[CONF_TOKEN] == "token"


async def test_websocket_closed_on_unload(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_lamarzocco: MagicMock,
) -> None:
    """Test the websocket is closed on unload."""
    mock_disconnect_callback = AsyncMock()
    mock_websocket = MagicMock()
    mock_websocket.closed = True

    mock_lamarzocco.websocket = WebSocketDetails(
        mock_websocket, mock_disconnect_callback
    )

    await async_init_integration(menuai, mock_config_entry)
    mock_lamarzocco.connect_dashboard_websocket.assert_called_once()
    mock_websocket.closed = False

    menuai.bus.async_fire(EVENT_menuai_STOP)
    await menuai.async_block_till_done()
    mock_disconnect_callback.assert_called_once()


@pytest.mark.parametrize(
    ("version", "issue_exists"), [("v3.5-rc6", True), ("v5.0.9", False)]
)
async def test_gateway_version_issue(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_cloud_client: MagicMock,
    version: str,
    issue_exists: bool,
) -> None:
    """Make sure we get the issue for certain gateway firmware versions."""
    mock_cloud_client.get_thing_settings.return_value.firmwares[
        FirmwareType.GATEWAY
    ].build_version = version

    await async_init_integration(menuai, mock_config_entry)

    issue_registry = ir.async_get(menuai)
    issue = issue_registry.async_get_issue(DOMAIN, "unsupported_gateway_firmware")
    assert (issue is not None) == issue_exists


async def test_device(
    menuai: menuai,
    mock_lamarzocco: MagicMock,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the device."""
    mock_config_entry = MockConfigEntry(
        title="My LaMarzocco",
        domain=DOMAIN,
        version=3,
        data=USER_INPUT
        | {
            CONF_ADDRESS: "00:00:00:00:00:00",
            CONF_TOKEN: "token",
            CONF_MAC: "aa:bb:cc:dd:ee:ff",
        },
        unique_id=mock_lamarzocco.serial_number,
    )
    await async_init_integration(menuai, mock_config_entry)

    menuai.config_entries.async_update_entry(
        mock_config_entry,
        data={
            **mock_config_entry.data,
        },
    )

    state = menuai.states.get(f"switch.{mock_lamarzocco.serial_number}")
    assert state

    entry = entity_registry.async_get(state.entity_id)
    assert entry
    assert entry.device_id

    device = device_registry.async_get(entry.device_id)
    assert device
    assert device == snapshot
