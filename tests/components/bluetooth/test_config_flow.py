"""Test the bluetooth config flow."""

from unittest.mock import patch

from bluetooth_adapters import DEFAULT_ADDRESS, AdapterDetails
import pytest

from menuai import config_entries
from menuai.components.bluetooth import HaBluetoothConnector
from menuai.components.bluetooth.const import (
    CONF_ADAPTER,
    CONF_DETAILS,
    CONF_PASSIVE,
    CONF_SOURCE,
    CONF_SOURCE_CONFIG_ENTRY_ID,
    CONF_SOURCE_DEVICE_ID,
    CONF_SOURCE_DOMAIN,
    CONF_SOURCE_MODEL,
    DOMAIN,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import area_registry as ar, device_registry as dr
from menuai.setup import async_setup_component

from . import FakeRemoteScanner, MockBleakClient, _get_manager

from tests.common import MockConfigEntry
from tests.typing import WebSocketGenerator


@pytest.mark.usefixtures(
    "macos_adapter", "mock_bleak_scanner_start", "mock_bluetooth_adapters"
)
async def test_options_flow_disabled_not_setup(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test options are disabled if the integration has not been setup."""
    await async_setup_component(menuai, "config", {})
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, options={}, unique_id=DEFAULT_ADDRESS
    )
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    ws_client = await menuai_ws_client(menuai)

    await ws_client.send_json(
        {
            "id": 5,
            "type": "config_entries/get",
            "domain": "bluetooth",
        }
    )
    response = await ws_client.receive_json()
    assert response["result"][0]["supports_options"] is False
    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("macos_adapter")
async def test_async_step_user_macos(menuai: menuai) -> None:
    """Test setting up manually with one adapter on MacOS."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "single_adapter"
    with (
        patch("menuai.components.bluetooth.async_setup", return_value=True),
        patch(
            "menuai.components.bluetooth.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Apple Unknown MacOS Model (Core Bluetooth)"
    assert result2["data"] == {}
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.usefixtures("one_adapter")
async def test_async_step_user_linux_one_adapter(menuai: menuai) -> None:
    """Test setting up manually with one adapter on Linux."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "single_adapter"
    assert result["description_placeholders"] == {
        "name": "hci0 (00:00:00:00:00:01)",
        "model": "Bluetooth Adapter 5.0 (cc01:aa01)",
        "manufacturer": "ACME",
    }
    with (
        patch("menuai.components.bluetooth.async_setup", return_value=True),
        patch(
            "menuai.components.bluetooth.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "ACME Bluetooth Adapter 5.0 (00:00:00:00:00:01)"
    assert result2["data"] == {}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_async_step_user_linux_crashed_adapter(
    menuai: menuai, crashed_adapter: None
) -> None:
    """Test setting up manually with one crashed adapter on Linux."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_adapters"


@pytest.mark.usefixtures("two_adapters")
async def test_async_step_user_linux_two_adapters(menuai: menuai) -> None:
    """Test setting up manually with two adapters on Linux."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "multiple_adapters"
    assert result["data_schema"].schema["adapter"].container == {
        "hci0": "hci0 (00:00:00:00:00:01) ACME Bluetooth Adapter 5.0 (cc01:aa01)",
        "hci1": "hci1 (00:00:00:00:00:02) ACME Bluetooth Adapter 5.0 (cc01:aa01)",
    }
    with (
        patch("menuai.components.bluetooth.async_setup", return_value=True),
        patch(
            "menuai.components.bluetooth.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_ADAPTER: "hci1"}
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "ACME Bluetooth Adapter 5.0 (00:00:00:00:00:02)"
    assert result2["data"] == {}
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.usefixtures("macos_adapter")
async def test_async_step_user_only_allows_one(menuai: menuai) -> None:
    """Test setting up manually with an existing entry."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DEFAULT_ADDRESS)
    entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_adapters"


async def test_async_step_integration_discovery(menuai: menuai) -> None:
    """Test setting up from integration discovery."""

    details = AdapterDetails(
        address="00:00:00:00:00:01",
        sw_version="1.23.5",
        hw_version="1.2.3",
        manufacturer="ACME",
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data={CONF_ADAPTER: "hci0", CONF_DETAILS: details},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["description_placeholders"] == {
        "name": "hci0 (00:00:00:00:00:01)",
        "model": "Unknown",
        "manufacturer": "ACME",
    }
    assert result["step_id"] == "single_adapter"
    with (
        patch("menuai.components.bluetooth.async_setup", return_value=True),
        patch(
            "menuai.components.bluetooth.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "ACME Unknown (00:00:00:00:00:01)"
    assert result2["data"] == {}
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.usefixtures("one_adapter")
async def test_async_step_integration_discovery_during_onboarding_one_adapter(
    menuai: menuai,
) -> None:
    """Test setting up from integration discovery during onboarding."""
    details = AdapterDetails(
        address="00:00:00:00:00:01",
        sw_version="1.23.5",
        hw_version="1.2.3",
        manufacturer="ACME",
    )

    with (
        patch("menuai.components.bluetooth.async_setup", return_value=True),
        patch(
            "menuai.components.bluetooth.async_setup_entry", return_value=True
        ) as mock_setup_entry,
        patch(
            "menuai.components.onboarding.async_is_onboarded",
            return_value=False,
        ) as mock_onboarding,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={CONF_ADAPTER: "hci0", CONF_DETAILS: details},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ACME Unknown (00:00:00:00:00:01)"
    assert result["data"] == {}
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_onboarding.mock_calls) == 1


@pytest.mark.usefixtures("two_adapters")
async def test_async_step_integration_discovery_during_onboarding_two_adapters(
    menuai: menuai,
) -> None:
    """Test setting up from integration discovery during onboarding."""
    details1 = AdapterDetails(
        address="00:00:00:00:00:01",
        sw_version="1.23.5",
        hw_version="1.2.3",
        manufacturer="ACME",
    )
    details2 = AdapterDetails(
        address="00:00:00:00:00:02",
        sw_version="1.23.5",
        hw_version="1.2.3",
        manufacturer="ACME",
    )

    with (
        patch("menuai.components.bluetooth.async_setup", return_value=True),
        patch(
            "menuai.components.bluetooth.async_setup_entry", return_value=True
        ) as mock_setup_entry,
        patch(
            "menuai.components.onboarding.async_is_onboarded",
            return_value=False,
        ) as mock_onboarding,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={CONF_ADAPTER: "hci0", CONF_DETAILS: details1},
        )
        result2 = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={CONF_ADAPTER: "hci1", CONF_DETAILS: details2},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ACME Unknown (00:00:00:00:00:01)"
    assert result["data"] == {}

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "ACME Unknown (00:00:00:00:00:02)"
    assert result2["data"] == {}

    assert len(mock_setup_entry.mock_calls) == 2
    assert len(mock_onboarding.mock_calls) == 2


@pytest.mark.usefixtures("macos_adapter")
async def test_async_step_integration_discovery_during_onboarding(
    menuai: menuai,
) -> None:
    """Test setting up from integration discovery during onboarding."""
    details = AdapterDetails(
        address=DEFAULT_ADDRESS,
        sw_version="1.23.5",
        hw_version="1.2.3",
        manufacturer="ACME",
    )

    with (
        patch("menuai.components.bluetooth.async_setup", return_value=True),
        patch(
            "menuai.components.bluetooth.async_setup_entry", return_value=True
        ) as mock_setup_entry,
        patch(
            "menuai.components.onboarding.async_is_onboarded",
            return_value=False,
        ) as mock_onboarding,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={CONF_ADAPTER: "Core Bluetooth", CONF_DETAILS: details},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ACME Unknown (Core Bluetooth)"
    assert result["data"] == {}
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_onboarding.mock_calls) == 1


async def test_async_step_integration_discovery_already_exists(
    menuai: menuai,
) -> None:
    """Test setting up from integration discovery when an entry already exists."""
    details = AdapterDetails(
        address="00:00:00:00:00:01",
        sw_version="1.23.5",
        hw_version="1.2.3",
        manufacturer="ACME",
    )

    entry = MockConfigEntry(domain=DOMAIN, unique_id="00:00:00:00:00:01")
    entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data={CONF_ADAPTER: "hci0", CONF_DETAILS: details},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.usefixtures(
    "one_adapter", "mock_bleak_scanner_start", "mock_bluetooth_adapters"
)
async def test_options_flow_linux(menuai: menuai) -> None:
    """Test options on Linux."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={},
        unique_id="00:00:00:00:00:01",
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] is None

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_PASSIVE: True,
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PASSIVE] is True

    # Verify we can change it to False

    result = await menuai.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] is None

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_PASSIVE: False,
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PASSIVE] is False
    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures(
    "macos_adapter", "mock_bleak_scanner_start", "mock_bluetooth_adapters"
)
async def test_options_flow_disabled_macos(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test options are disabled on MacOS."""
    await async_setup_component(menuai, "config", {})
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, options={}, unique_id=DEFAULT_ADDRESS
    )
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    ws_client = await menuai_ws_client(menuai)

    await ws_client.send_json(
        {
            "id": 5,
            "type": "config_entries/get",
            "domain": "bluetooth",
        }
    )
    response = await ws_client.receive_json()
    assert response["result"][0]["supports_options"] is False
    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures(
    "one_adapter", "mock_bleak_scanner_start", "mock_bluetooth_adapters"
)
async def test_options_flow_enabled_linux(
    menuai: menuai, menuai_ws_client: WebSocketGenerator
) -> None:
    """Test options are enabled on Linux."""
    await async_setup_component(menuai, "config", {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={},
        unique_id="00:00:00:00:00:01",
    )
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    ws_client = await menuai_ws_client(menuai)

    await ws_client.send_json(
        {
            "id": 5,
            "type": "config_entries/get",
            "domain": "bluetooth",
        }
    )
    response = await ws_client.receive_json()
    assert response["result"][0]["supports_options"] is True
    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures(
    "one_adapter", "mock_bleak_scanner_start", "mock_bluetooth_adapters"
)
async def test_options_flow_remote_adapter(menuai: menuai) -> None:
    """Test options are not available for remote adapters."""
    source_entry = MockConfigEntry(
        domain="test",
    )
    source_entry.add_to_menuai(menuai)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_SOURCE: "BB:BB:BB:BB:BB:BB",
            CONF_SOURCE_DOMAIN: "test",
            CONF_SOURCE_MODEL: "test",
            CONF_SOURCE_CONFIG_ENTRY_ID: source_entry.entry_id,
        },
        options={},
        unique_id="BB:BB:BB:BB:BB:BB",
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "remote_adapters_not_supported"
    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures(
    "one_adapter", "mock_bleak_scanner_start", "mock_bluetooth_adapters"
)
async def test_options_flow_local_no_passive_support(menuai: menuai) -> None:
    """Test options are not available for local adapters without passive support."""
    source_entry = MockConfigEntry(
        domain="test",
    )
    source_entry.add_to_menuai(menuai)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={},
        unique_id="BB:BB:BB:BB:BB:BB",
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    _get_manager()._adapters["hci0"]["passive_scan"] = False

    result = await menuai.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "local_adapters_no_passive_support"
    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("one_adapter")
async def test_async_step_user_linux_adapter_replace_ignored(
    menuai: menuai,
) -> None:
    """Test we can replace an ignored adapter from user flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="00:00:00:00:00:01",
        source=config_entries.SOURCE_IGNORE,
    )
    entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={},
    )
    with (
        patch("menuai.components.bluetooth.async_setup", return_value=True),
        patch(
            "menuai.components.bluetooth.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "ACME Bluetooth Adapter 5.0 (00:00:00:00:00:01)"
    assert result2["data"] == {}
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.usefixtures("enable_bluetooth")
async def test_async_step_integration_discovery_remote_adapter(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    area_registry: ar.AreaRegistry,
) -> None:
    """Test remote adapter configuration via integration discovery."""
    entry = MockConfigEntry(domain="test")
    entry.add_to_menuai(menuai)
    connector = (
        HaBluetoothConnector(MockBleakClient, "mock_bleak_client", lambda: False),
    )
    scanner = FakeRemoteScanner("esp32", "esp32", connector, True)
    manager = _get_manager()
    area_entry = area_registry.async_get_or_create("test")
    cancel_scanner = manager.async_register_scanner(scanner)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("test", "BB:BB:BB:BB:BB:BB")},
        suggested_area=area_entry.id,
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data={
            CONF_SOURCE: scanner.source,
            CONF_SOURCE_DOMAIN: "test",
            CONF_SOURCE_MODEL: "test",
            CONF_SOURCE_CONFIG_ENTRY_ID: entry.entry_id,
            CONF_SOURCE_DEVICE_ID: device_entry.id,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "esp32"
    assert result["data"] == {
        CONF_SOURCE: scanner.source,
        CONF_SOURCE_DOMAIN: "test",
        CONF_SOURCE_MODEL: "test",
        CONF_SOURCE_CONFIG_ENTRY_ID: entry.entry_id,
        CONF_SOURCE_DEVICE_ID: device_entry.id,
    }
    await menuai.async_block_till_done()

    new_entry_id: str = result["result"].entry_id
    new_entry = menuai.config_entries.async_get_entry(new_entry_id)
    assert new_entry is not None
    assert new_entry.state is config_entries.ConfigEntryState.LOADED

    ble_device_entry = device_registry.async_get_device(
        connections={(dr.CONNECTION_BLUETOOTH, scanner.source)}
    )
    assert ble_device_entry is not None
    assert ble_device_entry.via_device_id == device_entry.id
    assert ble_device_entry.area_id == area_entry.id

    await menuai.config_entries.async_unload(new_entry.entry_id)
    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    cancel_scanner()
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("enable_bluetooth")
async def test_async_step_integration_discovery_remote_adapter_mac_fix(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    area_registry: ar.AreaRegistry,
) -> None:
    """Test remote adapter corrects mac address via integration discovery."""
    entry = MockConfigEntry(domain="test")
    entry.add_to_menuai(menuai)
    bluetooth_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_SOURCE: "AA:BB:CC:DD:EE:FF",
            CONF_SOURCE_DOMAIN: "test",
            CONF_SOURCE_MODEL: "test",
            CONF_SOURCE_CONFIG_ENTRY_ID: entry.entry_id,
            CONF_SOURCE_DEVICE_ID: None,
        },
    )
    bluetooth_entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data={
            CONF_SOURCE: "AA:AA:AA:AA:AA:AA",
            CONF_SOURCE_DOMAIN: "test",
            CONF_SOURCE_MODEL: "test",
            CONF_SOURCE_CONFIG_ENTRY_ID: entry.entry_id,
            CONF_SOURCE_DEVICE_ID: None,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert bluetooth_entry.unique_id == "AA:AA:AA:AA:AA:AA"
    assert bluetooth_entry.data[CONF_SOURCE] == "AA:AA:AA:AA:AA:AA"
