"""Test init of GIOS integration."""

import json
from unittest.mock import patch

from menuai.components.air_quality import DOMAIN as AIR_QUALITY_PLATFORM
from menuai.components.gios.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from . import STATIONS, init_integration

from tests.common import MockConfigEntry, async_load_fixture


async def test_async_setup_entry(menuai: menuai) -> None:
    """Test a successful setup entry."""
    await init_integration(menuai)

    state = menuai.states.get("sensor.home_pm2_5")
    assert state is not None
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "4"


async def test_config_not_ready(menuai: menuai) -> None:
    """Test for setup failure if connection to GIOS is missing."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id=123,
        data={"station_id": 123, "name": "Home"},
    )

    with patch(
        "menuai.components.gios.coordinator.Gios._get_stations",
        side_effect=ConnectionError(),
    ):
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(menuai: menuai) -> None:
    """Test successful unload of entry."""
    entry = await init_integration(menuai)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_migrate_device_and_config_entry(
    menuai: menuai, device_registry: dr.DeviceRegistry
) -> None:
    """Test device_info identifiers and config entry migration."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id=123,
        data={
            "station_id": 123,
            "name": "Home",
        },
    )

    indexes = json.loads(await async_load_fixture(menuai, "indexes.json", DOMAIN))
    station = json.loads(await async_load_fixture(menuai, "station.json", DOMAIN))
    sensors = json.loads(await async_load_fixture(menuai, "sensors.json", DOMAIN))

    with (
        patch(
            "menuai.components.gios.coordinator.Gios._get_stations",
            return_value=STATIONS,
        ),
        patch(
            "menuai.components.gios.coordinator.Gios._get_station",
            return_value=station,
        ),
        patch(
            "menuai.components.gios.coordinator.Gios._get_all_sensors",
            return_value=sensors,
        ),
        patch(
            "menuai.components.gios.coordinator.Gios._get_indexes",
            return_value=indexes,
        ),
    ):
        config_entry.add_to_menuai(menuai)

        device_entry = device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id, identifiers={(DOMAIN, 123)}
        )

        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        migrated_device_entry = device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id, identifiers={(DOMAIN, "123")}
        )
        assert device_entry.id == migrated_device_entry.id


async def test_remove_air_quality_entities(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test remove air_quality entities from registry."""
    entity_registry.async_get_or_create(
        AIR_QUALITY_PLATFORM,
        DOMAIN,
        "123",
        suggested_object_id="home",
        disabled_by=None,
    )

    await init_integration(menuai)

    entry = entity_registry.async_get("air_quality.home")
    assert entry is None
