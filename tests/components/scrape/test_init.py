"""Test Scrape component setup process."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from menuai.components.scrape.const import DEFAULT_SCAN_INTERVAL, DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from . import MockRestData, return_integration_config

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.typing import WebSocketGenerator


async def test_setup_config(menuai: menuai) -> None:
    """Test setup from yaml."""
    config = {
        DOMAIN: [
            return_integration_config(
                sensors=[{"select": ".current-version h1", "name": "HA version"}]
            )
        ]
    }

    mocker = MockRestData("test_scrape_sensor")
    with patch(
        "menuai.components.rest.RestData",
        return_value=mocker,
    ) as mock_setup:
        assert await async_setup_component(menuai, DOMAIN, config)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.ha_version")
    assert state.state == "Current Version: 2021.12.10"

    assert len(mock_setup.mock_calls) == 1


async def test_setup_no_data_fails_with_recovery(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test setup entry no data fails and recovers."""
    config = {
        DOMAIN: [
            return_integration_config(
                sensors=[{"select": ".current-version h1", "name": "HA version"}]
            ),
        ]
    }

    mocker = MockRestData("test_scrape_sensor_no_data")
    with patch(
        "menuai.components.rest.RestData",
        return_value=mocker,
    ):
        assert await async_setup_component(menuai, DOMAIN, config)
        await menuai.async_block_till_done()

        state = menuai.states.get("sensor.ha_version")
        assert state is None

        assert "Platform scrape not ready yet" in caplog.text

        mocker.payload = "test_scrape_sensor"
        async_fire_time_changed(menuai, dt_util.utcnow() + DEFAULT_SCAN_INTERVAL)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.ha_version")
    assert state.state == "Current Version: 2021.12.10"


async def test_setup_config_no_configuration(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test setup from yaml missing configuration options."""
    config = {DOMAIN: None}

    assert await async_setup_component(menuai, DOMAIN, config)
    await menuai.async_block_till_done()

    assert entity_registry.entities == {}


async def test_setup_config_no_sensors(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test setup from yaml with no configured sensors finalize properly."""
    config = {
        DOMAIN: [
            {
                "resource": "https://www.address.com",
                "verify_ssl": True,
            },
            {
                "resource": "https://www.address2.com",
                "verify_ssl": True,
                "sensor": None,
            },
        ]
    }

    mocker = MockRestData("test_scrape_sensor")
    with patch(
        "menuai.components.rest.RestData",
        return_value=mocker,
    ):
        assert await async_setup_component(menuai, DOMAIN, config)
        await menuai.async_block_till_done()


async def test_setup_entry(menuai: menuai, loaded_entry: MockConfigEntry) -> None:
    """Test setup entry."""

    assert loaded_entry.state is ConfigEntryState.LOADED


async def test_unload_entry(menuai: menuai, loaded_entry: MockConfigEntry) -> None:
    """Test unload an entry."""

    assert loaded_entry.state is ConfigEntryState.LOADED
    assert await menuai.config_entries.async_unload(loaded_entry.entry_id)
    await menuai.async_block_till_done()
    assert loaded_entry.state is ConfigEntryState.NOT_LOADED


async def test_device_remove_devices(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    loaded_entry: MockConfigEntry,
    menuai_ws_client: WebSocketGenerator,
) -> None:
    """Test we can only remove a device that no longer exists."""
    assert await async_setup_component(menuai, "config", {})
    entity = entity_registry.entities["sensor.current_version"]

    device_entry = device_registry.async_get(entity.device_id)
    client = await menuai_ws_client(menuai)
    response = await client.remove_device(device_entry.id, loaded_entry.entry_id)
    assert not response["success"]

    dead_device_entry = device_registry.async_get_or_create(
        config_entry_id=loaded_entry.entry_id,
        identifiers={(DOMAIN, "remove-device-id")},
    )
    response = await client.remove_device(dead_device_entry.id, loaded_entry.entry_id)
    assert response["success"]
