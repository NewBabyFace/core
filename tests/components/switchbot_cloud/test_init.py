"""Tests for the SwitchBot Cloud integration init."""

from unittest.mock import patch

import pytest
from switchbot_api import (
    Device,
    PowerState,
    Remote,
    SwitchBotAuthenticationError,
    SwitchBotConnectionError,
)

from menuai.components.switchbot_cloud import SwitchBotAPI
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_WEBHOOK_ID, EVENT_menuai_START
from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config

from . import configure_integration

from tests.typing import ClientSessionGenerator


@pytest.fixture
def mock_list_devices():
    """Mock list_devices."""
    with patch.object(SwitchBotAPI, "list_devices") as mock_list_devices:
        yield mock_list_devices


@pytest.fixture
def mock_get_status():
    """Mock get_status."""
    with patch.object(SwitchBotAPI, "get_status") as mock_get_status:
        yield mock_get_status


@pytest.fixture
def mock_get_webook_configuration():
    """Mock get_status."""
    with patch.object(
        SwitchBotAPI, "get_webook_configuration"
    ) as mock_get_webook_configuration:
        yield mock_get_webook_configuration


@pytest.fixture
def mock_delete_webhook():
    """Mock get_status."""
    with patch.object(SwitchBotAPI, "delete_webhook") as mock_delete_webhook:
        yield mock_delete_webhook


@pytest.fixture
def mock_setup_webhook():
    """Mock get_status."""
    with patch.object(SwitchBotAPI, "setup_webhook") as mock_setup_webhook:
        yield mock_setup_webhook


async def test_setup_entry_success(
    menuai: menuai,
    mock_list_devices,
    mock_get_status,
    mock_get_webook_configuration,
    mock_delete_webhook,
    mock_setup_webhook,
) -> None:
    """Test successful setup of entry."""
    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://example.com"},
    )
    mock_get_webook_configuration.return_value = {"urls": ["https://example.com"]}
    mock_list_devices.return_value = [
        Remote(
            version="V1.0",
            deviceId="air-conditonner-id-1",
            deviceName="air-conditonner-name-1",
            remoteType="Air Conditioner",
            hubDeviceId="test-hub-id",
        ),
        Device(
            version="V1.0",
            deviceId="plug-id-1",
            deviceName="plug-name-1",
            deviceType="Plug",
            hubDeviceId="test-hub-id",
        ),
        Remote(
            version="V1.0",
            deviceId="plug-id-2",
            deviceName="plug-name-2",
            remoteType="DIY Plug",
            hubDeviceId="test-hub-id",
        ),
        Remote(
            version="V1.0",
            deviceId="meter-pro-1",
            deviceName="meter-pro-name-1",
            deviceType="MeterPro(CO2)",
            hubDeviceId="test-hub-id",
        ),
        Remote(
            version="V1.0",
            deviceId="hub2-1",
            deviceName="hub2-name-1",
            deviceType="Hub 2",
            hubDeviceId="test-hub-id",
        ),
        Device(
            deviceId="vacuum-1",
            deviceName="vacuum-name-1",
            deviceType="K10+",
            hubDeviceId=None,
        ),
    ]
    mock_get_status.return_value = {"power": PowerState.ON.value}

    entry = await configure_integration(menuai)
    assert entry.state is ConfigEntryState.LOADED

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    mock_list_devices.assert_called_once()
    mock_get_status.assert_called()
    mock_get_webook_configuration.assert_called_once()
    mock_delete_webhook.assert_called_once()
    mock_setup_webhook.assert_called_once()


@pytest.mark.parametrize(
    ("error", "state"),
    [
        (SwitchBotAuthenticationError, ConfigEntryState.SETUP_ERROR),
        (SwitchBotConnectionError, ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_setup_entry_fails_when_listing_devices(
    menuai: menuai,
    error: Exception,
    state: ConfigEntryState,
    mock_list_devices,
    mock_get_status,
) -> None:
    """Test error handling when list_devices in setup of entry."""
    mock_list_devices.side_effect = error
    entry = await configure_integration(menuai)
    assert entry.state == state

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    mock_list_devices.assert_called_once()
    mock_get_status.assert_not_called()


async def test_setup_entry_fails_when_refreshing(
    menuai: menuai, mock_list_devices, mock_get_status
) -> None:
    """Test error handling in get_status in setup of entry."""
    mock_list_devices.return_value = [
        Device(
            version="V1.0",
            deviceId="test-id",
            deviceName="test-name",
            deviceType="Plug",
            hubDeviceId="test-hub-id",
        )
    ]
    mock_get_status.side_effect = SwitchBotConnectionError
    entry = await configure_integration(menuai)
    assert entry.state is ConfigEntryState.SETUP_RETRY

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    mock_list_devices.assert_called_once()
    mock_get_status.assert_called()


async def test_posting_to_webhook(
    menuai: menuai,
    mock_list_devices,
    mock_get_status,
    mock_get_webook_configuration,
    mock_delete_webhook,
    mock_setup_webhook,
    menuai_client_no_auth: ClientSessionGenerator,
) -> None:
    """Test handler webhook call."""
    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://example.com"},
    )
    mock_get_webook_configuration.return_value = {"urls": ["https://example.com"]}
    mock_list_devices.return_value = [
        Device(
            deviceId="vacuum-1",
            deviceName="vacuum-name-1",
            deviceType="K10+",
            hubDeviceId=None,
        ),
    ]
    mock_get_status.return_value = {"power": PowerState.ON.value}
    mock_delete_webhook.return_value = {}
    mock_setup_webhook.return_value = {}

    entry = await configure_integration(menuai)
    assert entry.state is ConfigEntryState.LOADED

    menuai.bus.async_fire(EVENT_menuai_START)

    webhook_id = entry.data[CONF_WEBHOOK_ID]
    client = await menuai_client_no_auth()
    # fire webhook
    await client.post(
        f"/api/webhook/{webhook_id}",
        json={
            "eventType": "changeReport",
            "eventVersion": "1",
            "context": {"deviceType": "...", "deviceMac": "vacuum-1"},
        },
    )

    await menuai.async_block_till_done()

    mock_setup_webhook.assert_called_once()
