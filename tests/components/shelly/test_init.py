"""Test cases for the Shelly component."""

from ipaddress import IPv4Address
from unittest.mock import AsyncMock, Mock, call, patch

from aioshelly.block_device import COAP
from aioshelly.common import ConnectionOptions
from aioshelly.const import MODEL_PLUS_2PM
from aioshelly.exceptions import (
    DeviceConnectionError,
    InvalidAuthError,
    MacAddressMismatchError,
    RpcCallError,
)
from aioshelly.rpc_device.utils import bluetooth_mac_from_primary_mac
import pytest

from menuai.components.shelly.const import (
    BLE_SCANNER_FIRMWARE_UNSUPPORTED_ISSUE_ID,
    BLE_SCANNER_MIN_FIRMWARE,
    BLOCK_EXPECTED_SLEEP_PERIOD,
    BLOCK_WRONG_SLEEP_PERIOD,
    CONF_BLE_SCANNER_MODE,
    CONF_GEN,
    CONF_SLEEP_PERIOD,
    DOMAIN,
    MODELS_WITH_WRONG_SLEEP_PERIOD,
    BLEScannerMode,
)
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_PORT,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.helpers import issue_registry as ir
from menuai.helpers.device_registry import DeviceRegistry, format_mac
from menuai.setup import async_setup_component

from . import MOCK_MAC, init_integration, mutate_rpc_device_status


async def test_custom_coap_port(
    menuai: menuai, mock_block_device: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test custom coap port."""
    assert await async_setup_component(
        menuai,
        DOMAIN,
        {DOMAIN: {"coap_port": 7632}},
    )
    await menuai.async_block_till_done()

    await init_integration(menuai, 1)
    assert "Starting CoAP context with UDP port 7632" in caplog.text


async def test_ip_address_with_only_default_interface(
    menuai: menuai, mock_block_device: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test more local ip addresses with only the default interface.."""
    with (
        patch(
            "menuai.components.network.async_only_default_interface_enabled",
            return_value=True,
        ),
        patch(
            "menuai.components.network.async_get_enabled_source_ips",
            return_value=[IPv4Address("192.168.1.10"), IPv4Address("10.10.10.10")],
        ),
        patch(
            "menuai.components.shelly.utils.COAP",
            autospec=COAP,
        ) as mock_coap_init,
    ):
        assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {"coap_port": 7632}})
        await menuai.async_block_till_done()

        await init_integration(menuai, 1)
        assert "Starting CoAP context with UDP port 7632" in caplog.text
        # Make sure COAP.initialize is called with an empty list
        # when async_only_default_interface_enabled is True even if
        # async_get_enabled_source_ips returns more than one address
        assert mock_coap_init.mock_calls[1] == call().initialize(7632, [])


async def test_ip_address_without_only_default_interface(
    menuai: menuai, mock_block_device: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test more local ip addresses without only the default interface.."""
    with (
        patch(
            "menuai.components.network.async_only_default_interface_enabled",
            return_value=False,
        ),
        patch(
            "menuai.components.network.async_get_enabled_source_ips",
            return_value=[IPv4Address("192.168.1.10"), IPv4Address("10.10.10.10")],
        ),
        patch(
            "menuai.components.shelly.utils.COAP",
            autospec=COAP,
        ) as mock_coap_init,
    ):
        assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {"coap_port": 7632}})
        await menuai.async_block_till_done()

        await init_integration(menuai, 1)
        assert "Starting CoAP context with UDP port 7632" in caplog.text
        assert mock_coap_init.mock_calls[1] == call().initialize(
            7632, [IPv4Address("192.168.1.10"), IPv4Address("10.10.10.10")]
        )


@pytest.mark.parametrize("gen", [1, 2, 3])
async def test_shared_device_mac(
    menuai: menuai,
    gen: int,
    mock_block_device: Mock,
    mock_rpc_device: Mock,
    device_registry: DeviceRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test first time shared device with another domain."""
    await init_integration(menuai, gen, sleep_period=1000)
    assert "will resume when device is online" in caplog.text


async def test_setup_entry_not_shelly(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test not Shelly entry."""
    await init_integration(menuai, 1, data={})
    assert "probably comes from a custom integration" in caplog.text


@pytest.mark.parametrize("gen", [1, 2, 3])
async def test_device_connection_error(
    menuai: menuai,
    gen: int,
    mock_block_device: Mock,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test device connection error."""
    monkeypatch.setattr(
        mock_block_device, "initialize", AsyncMock(side_effect=DeviceConnectionError)
    )
    monkeypatch.setattr(
        mock_rpc_device, "initialize", AsyncMock(side_effect=DeviceConnectionError)
    )

    entry = await init_integration(menuai, gen)
    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize("gen", [1, 2, 3])
async def test_device_unsupported_firmware(
    menuai: menuai,
    gen: int,
    mock_block_device: Mock,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test device init with unsupported firmware."""
    monkeypatch.setattr(mock_block_device, "firmware_supported", False)
    monkeypatch.setattr(mock_rpc_device, "firmware_supported", False)

    entry = await init_integration(menuai, gen)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert (
        DOMAIN,
        "firmware_unsupported_123456789ABC",
    ) in issue_registry.issues


@pytest.mark.parametrize("gen", [1, 2, 3])
async def test_mac_mismatch_error(
    menuai: menuai,
    gen: int,
    mock_block_device: Mock,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test device MAC address mismatch error."""
    monkeypatch.setattr(
        mock_block_device, "initialize", AsyncMock(side_effect=MacAddressMismatchError)
    )
    monkeypatch.setattr(
        mock_rpc_device, "initialize", AsyncMock(side_effect=MacAddressMismatchError)
    )

    entry = await init_integration(menuai, gen)
    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize("gen", [1, 2, 3])
async def test_device_auth_error(
    menuai: menuai,
    gen: int,
    mock_block_device: Mock,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test device authentication error."""
    monkeypatch.setattr(
        mock_block_device, "initialize", AsyncMock(side_effect=InvalidAuthError)
    )
    monkeypatch.setattr(
        mock_rpc_device, "initialize", AsyncMock(side_effect=InvalidAuthError)
    )

    entry = await init_integration(menuai, gen)
    assert entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    flow = flows[0]
    assert flow.get("step_id") == "reauth_confirm"
    assert flow.get("handler") == DOMAIN

    assert "context" in flow
    assert flow["context"].get("source") == SOURCE_REAUTH
    assert flow["context"].get("entry_id") == entry.entry_id


@pytest.mark.parametrize(("entry_sleep", "device_sleep"), [(None, 0), (3600, 3600)])
async def test_sleeping_block_device_online(
    menuai: menuai,
    entry_sleep: int | None,
    device_sleep: int,
    mock_block_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    device_registry: DeviceRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test sleeping block device online."""
    await init_integration(menuai, 1, data={})

    monkeypatch.setitem(
        mock_block_device.settings,
        "sleep_mode",
        {"period": int(device_sleep / 60), "unit": "m"},
    )
    entry = await init_integration(menuai, 1, sleep_period=entry_sleep)
    assert "will resume when device is online" in caplog.text

    mock_block_device.mock_online()
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "online, resuming setup" in caplog.text
    assert entry.data[CONF_SLEEP_PERIOD] == device_sleep


@pytest.mark.parametrize(("entry_sleep", "device_sleep"), [(None, 0), (1000, 1000)])
async def test_sleeping_rpc_device_online(
    menuai: menuai,
    entry_sleep: int | None,
    device_sleep: int,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test sleeping RPC device online."""
    monkeypatch.setattr(mock_rpc_device, "connected", False)
    monkeypatch.setitem(mock_rpc_device.status["sys"], "wakeup_period", device_sleep)
    entry = await init_integration(menuai, 2, sleep_period=entry_sleep)
    assert "will resume when device is online" in caplog.text

    mock_rpc_device.mock_online()
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "online, resuming setup" in caplog.text
    assert entry.data[CONF_SLEEP_PERIOD] == device_sleep


async def test_sleeping_rpc_device_online_new_firmware(
    menuai: menuai,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test sleeping device Gen2 with firmware 1.0.0 or later."""
    monkeypatch.setattr(mock_rpc_device, "connected", False)
    entry = await init_integration(menuai, 2, sleep_period=None)
    assert "will resume when device is online" in caplog.text

    mutate_rpc_device_status(monkeypatch, mock_rpc_device, "sys", "wakeup_period", 1500)
    mock_rpc_device.mock_online()
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "online, resuming setup" in caplog.text
    assert entry.data[CONF_SLEEP_PERIOD] == 1500


async def test_sleeping_rpc_device_online_during_setup(
    menuai: menuai,
    mock_sleepy_rpc_device: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test sleeping device Gen2 woke up by user during setup."""
    await init_integration(menuai, 2, sleep_period=1000)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "will resume when device is online" in caplog.text
    assert "is online (source: setup)" in caplog.text

    assert menuai.states.get("sensor.test_name_temperature")


async def test_sleeping_rpc_device_offline_during_setup(
    menuai: menuai,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test sleeping device Gen2 woke up by user during setup."""
    monkeypatch.setattr(mock_rpc_device, "connected", False)
    monkeypatch.setitem(mock_rpc_device.status["sys"], "wakeup_period", 1000)
    monkeypatch.setattr(
        mock_rpc_device, "initialize", AsyncMock(side_effect=DeviceConnectionError)
    )

    # Init integration, should fail since device is offline
    await init_integration(menuai, 2, sleep_period=1000)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "will resume when device is online" in caplog.text
    assert "is online (source: setup)" in caplog.text
    assert menuai.states.get("sensor.test_name_temperature") is None

    # Create an online event and verify that device is init successfully
    monkeypatch.setattr(mock_rpc_device, "initialize", AsyncMock())
    mock_rpc_device.mock_online()
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert menuai.states.get("sensor.test_name_temperature")


@pytest.mark.parametrize(
    ("gen", "entity_id"),
    [
        (1, "switch.test_name_channel_1"),
        (2, "switch.test_name_test_switch_0"),
    ],
)
async def test_entry_unload(
    menuai: menuai,
    gen: int,
    entity_id: str,
    mock_block_device: Mock,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test entry unload."""
    monkeypatch.delitem(mock_rpc_device.status, "cover:0")
    monkeypatch.setitem(mock_rpc_device.status["sys"], "relay_in_thermostat", False)
    entry = await init_integration(menuai, gen)

    assert entry.state is ConfigEntryState.LOADED
    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_ON

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.parametrize(
    ("gen", "entity_id"),
    [
        (1, "switch.test_name_channel_1"),
        (2, "switch.test_name_test_switch_0"),
    ],
)
async def test_entry_unload_device_not_ready(
    menuai: menuai,
    gen: int,
    entity_id: str,
    mock_block_device: Mock,
    mock_rpc_device: Mock,
) -> None:
    """Test entry unload when device is not ready."""
    assert (entry := await init_integration(menuai, gen, sleep_period=1000))
    assert entry.state is ConfigEntryState.LOADED

    assert menuai.states.get(entity_id) is None

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_entry_unload_not_connected(
    menuai: menuai, mock_rpc_device: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test entry unload when not connected."""
    monkeypatch.delitem(mock_rpc_device.status, "cover:0")
    monkeypatch.setitem(mock_rpc_device.status["sys"], "relay_in_thermostat", False)

    with patch(
        "menuai.components.shelly.coordinator.async_stop_scanner"
    ) as mock_stop_scanner:
        assert (
            entry := await init_integration(
                menuai, 2, options={CONF_BLE_SCANNER_MODE: BLEScannerMode.ACTIVE}
            )
        )
        assert entry.state is ConfigEntryState.LOADED

        assert (state := menuai.states.get("switch.test_name_test_switch_0"))
        assert state.state == STATE_ON
        assert not mock_stop_scanner.call_count

        monkeypatch.setattr(mock_rpc_device, "connected", False)

        await menuai.config_entries.async_reload(entry.entry_id)
        await menuai.async_block_till_done()

    assert not mock_stop_scanner.call_count
    assert entry.state is ConfigEntryState.LOADED


async def test_entry_unload_not_connected_but_we_think_we_are(
    menuai: menuai, mock_rpc_device: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test entry unload when not connected but we think we are still connected."""
    monkeypatch.delitem(mock_rpc_device.status, "cover:0")
    monkeypatch.setitem(mock_rpc_device.status["sys"], "relay_in_thermostat", False)

    with patch(
        "menuai.components.shelly.coordinator.async_stop_scanner",
        side_effect=DeviceConnectionError,
    ) as mock_stop_scanner:
        assert (
            entry := await init_integration(
                menuai, 2, options={CONF_BLE_SCANNER_MODE: BLEScannerMode.ACTIVE}
            )
        )
        assert entry.state is ConfigEntryState.LOADED

        assert (state := menuai.states.get("switch.test_name_test_switch_0"))
        assert state.state == STATE_ON
        assert not mock_stop_scanner.call_count

        monkeypatch.setattr(mock_rpc_device, "connected", False)

        await menuai.config_entries.async_reload(entry.entry_id)
        await menuai.async_block_till_done()

    assert not mock_stop_scanner.call_count
    assert entry.state is ConfigEntryState.LOADED


async def test_no_attempt_to_stop_scanner_with_sleepy_devices(
    menuai: menuai, mock_rpc_device: Mock
) -> None:
    """Test we do not try to stop the scanner if its disabled with a sleepy device."""
    with patch(
        "menuai.components.shelly.coordinator.async_stop_scanner",
    ) as mock_stop_scanner:
        entry = await init_integration(menuai, 2, sleep_period=7200)
        assert entry.state is ConfigEntryState.LOADED
        assert not mock_stop_scanner.call_count

        mock_rpc_device.mock_update()
        await menuai.async_block_till_done()
        assert not mock_stop_scanner.call_count


async def test_entry_missing_gen(menuai: menuai, mock_block_device: Mock) -> None:
    """Test successful Gen1 device init when gen is missing in entry data."""
    entry = await init_integration(menuai, None)

    assert entry.state is ConfigEntryState.LOADED

    # num_outputs is 2, channel name is used
    assert (state := menuai.states.get("switch.test_name_channel_1"))
    assert state.state == STATE_ON


async def test_entry_missing_port(menuai: menuai) -> None:
    """Test successful Gen2 device init when port is missing in entry data."""
    data = {
        CONF_HOST: "192.168.1.37",
        CONF_SLEEP_PERIOD: 0,
        CONF_MODEL: MODEL_PLUS_2PM,
        CONF_GEN: 2,
    }
    entry = await init_integration(menuai, 2, data=data, skip_setup=True)
    with (
        patch("menuai.components.shelly.RpcDevice.initialize"),
        patch(
            "menuai.components.shelly.RpcDevice.create", return_value=Mock()
        ) as rpc_device_mock,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        assert rpc_device_mock.call_args[0][2] == ConnectionOptions(
            ip_address="192.168.1.37", device_mac="123456789ABC", port=80
        )


async def test_rpc_entry_custom_port(menuai: menuai) -> None:
    """Test successful Gen2 device init using custom port."""
    data = {
        CONF_HOST: "192.168.1.37",
        CONF_SLEEP_PERIOD: 0,
        CONF_MODEL: MODEL_PLUS_2PM,
        CONF_GEN: 2,
        CONF_PORT: 8001,
    }
    entry = await init_integration(menuai, 2, data=data, skip_setup=True)
    with (
        patch("menuai.components.shelly.RpcDevice.initialize"),
        patch(
            "menuai.components.shelly.RpcDevice.create", return_value=Mock()
        ) as rpc_device_mock,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        assert rpc_device_mock.call_args[0][2] == ConnectionOptions(
            ip_address="192.168.1.37", device_mac="123456789ABC", port=8001
        )


@pytest.mark.parametrize(("model"), MODELS_WITH_WRONG_SLEEP_PERIOD)
async def test_sleeping_block_device_wrong_sleep_period(
    menuai: menuai, mock_block_device: Mock, model: str
) -> None:
    """Test sleeping block device with wrong sleep period."""
    entry = await init_integration(
        menuai, 1, model=model, sleep_period=BLOCK_WRONG_SLEEP_PERIOD, skip_setup=True
    )
    assert entry.data[CONF_SLEEP_PERIOD] == BLOCK_WRONG_SLEEP_PERIOD
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.data[CONF_SLEEP_PERIOD] == BLOCK_EXPECTED_SLEEP_PERIOD


async def test_bluetooth_cleanup_on_remove_entry(
    menuai: menuai,
    mock_rpc_device: Mock,
) -> None:
    """Test bluetooth is cleaned up on entry removal."""
    entry = await init_integration(menuai, 2)

    assert entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    with patch("menuai.components.shelly.async_remove_scanner") as remove_mock:
        await menuai.config_entries.async_remove(entry.entry_id)
        await menuai.async_block_till_done()

    remove_mock.assert_called_once_with(
        menuai, format_mac(bluetooth_mac_from_primary_mac(entry.unique_id)).upper()
    )


async def test_device_script_getcode_error(
    menuai: menuai,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test device script get code error."""
    monkeypatch.setattr(
        mock_rpc_device, "script_getcode", AsyncMock(side_effect=RpcCallError(0))
    )

    entry = await init_integration(menuai, 2)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_ble_scanner_unsupported_firmware_fixed(
    menuai: menuai,
    mock_rpc_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test device init with unsupported firmware."""
    issue_id = BLE_SCANNER_FIRMWARE_UNSUPPORTED_ISSUE_ID.format(unique=MOCK_MAC)
    entry = await init_integration(
        menuai, 2, options={CONF_BLE_SCANNER_MODE: BLEScannerMode.ACTIVE}
    )

    assert issue_registry.async_get_issue(DOMAIN, issue_id)
    assert len(issue_registry.issues) == 1

    monkeypatch.setitem(mock_rpc_device.shelly, "ver", BLE_SCANNER_MIN_FIRMWARE)

    await menuai.config_entries.async_reload(entry.entry_id)
    await menuai.async_block_till_done()

    assert not issue_registry.async_get_issue(DOMAIN, issue_id)
    assert len(issue_registry.issues) == 0
