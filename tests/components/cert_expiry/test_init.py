"""Tests for Cert Expiry setup."""

from unittest.mock import patch

from freezegun import freeze_time

from menuai.components.cert_expiry.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import (
    CONF_HOST,
    CONF_PORT,
    EVENT_menuai_STARTED,
    STATE_UNAVAILABLE,
)
from menuai.core import CoreState, menuai
from menuai.setup import async_setup_component

from .const import HOST, PORT
from .helpers import future_timestamp, static_datetime

from tests.common import MockConfigEntry


async def test_update_unique_id(menuai: menuai) -> None:
    """Test updating a config entry without a unique_id."""
    assert menuai.state is CoreState.running

    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST, CONF_PORT: PORT})
    entry.add_to_menuai(menuai)

    config_entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(config_entries) == 1
    assert entry is config_entries[0]
    assert not entry.unique_id

    with patch(
        "menuai.components.cert_expiry.coordinator.get_cert_expiry_timestamp",
        return_value=future_timestamp(1),
    ):
        assert await async_setup_component(menuai, DOMAIN, {}) is True
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.unique_id == f"{HOST}:{PORT}"


@freeze_time(static_datetime())
async def test_unload_config_entry(menuai: menuai) -> None:
    """Test unloading a config entry."""
    assert menuai.state is CoreState.running

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PORT: PORT},
        unique_id=f"{HOST}:{PORT}",
    )
    entry.add_to_menuai(menuai)

    config_entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(config_entries) == 1
    assert entry is config_entries[0]

    timestamp = future_timestamp(100)
    with patch(
        "menuai.components.cert_expiry.coordinator.get_cert_expiry_timestamp",
        return_value=timestamp,
    ):
        assert await async_setup_component(menuai, DOMAIN, {}) is True
        menuai.bus.async_fire(EVENT_menuai_STARTED)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state.state == timestamp.isoformat()
    assert state.attributes.get("error") == "None"
    assert state.attributes.get("is_valid")

    await menuai.config_entries.async_unload(entry.entry_id)

    assert entry.state is ConfigEntryState.NOT_LOADED
    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state.state == STATE_UNAVAILABLE

    await menuai.config_entries.async_remove(entry.entry_id)
    await menuai.async_block_till_done()
    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state is None


async def test_delay_load_during_startup(menuai: menuai) -> None:
    """Test delayed loading of a config entry during startup."""
    menuai.set_state(CoreState.not_running)

    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST, CONF_PORT: PORT})
    entry.add_to_menuai(menuai)

    assert await async_setup_component(menuai, DOMAIN, {}) is True
    await menuai.async_block_till_done()

    assert menuai.state is CoreState.not_running
    assert entry.state is ConfigEntryState.LOADED

    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state is None

    timestamp = future_timestamp(100)
    with patch(
        "menuai.components.cert_expiry.coordinator.get_cert_expiry_timestamp",
        return_value=timestamp,
    ):
        await menuai.async_start()
        await menuai.async_block_till_done()

    assert menuai.state is CoreState.running

    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state.state == timestamp.isoformat()
    assert state.attributes.get("error") == "None"
    assert state.attributes.get("is_valid")
