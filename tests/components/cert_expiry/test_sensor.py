"""Tests for the Cert Expiry sensors."""

from datetime import timedelta
import socket
import ssl
from unittest.mock import patch

from freezegun import freeze_time

from menuai.components.cert_expiry.const import DOMAIN
from menuai.const import CONF_HOST, CONF_PORT, STATE_UNAVAILABLE, STATE_UNKNOWN
from menuai.core import CoreState, menuai
from menuai.util.dt import utcnow

from .const import HOST, PORT
from .helpers import future_timestamp, static_datetime

from tests.common import MockConfigEntry, async_fire_time_changed


@freeze_time(static_datetime())
async def test_async_setup_entry(menuai: menuai) -> None:
    """Test async_setup_entry."""
    assert menuai.state is CoreState.running

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PORT: PORT},
        unique_id=f"{HOST}:{PORT}",
    )

    timestamp = future_timestamp(100)

    with patch(
        "menuai.components.cert_expiry.coordinator.get_cert_expiry_timestamp",
        return_value=timestamp,
    ):
        entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state is not None
    assert state.state != STATE_UNAVAILABLE
    assert state.state == timestamp.isoformat()
    assert state.attributes.get("error") == "None"
    assert state.attributes.get("is_valid")


async def test_async_setup_entry_bad_cert(menuai: menuai) -> None:
    """Test async_setup_entry with a bad/expired cert."""
    assert menuai.state is CoreState.running

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PORT: PORT},
        unique_id=f"{HOST}:{PORT}",
    )

    with patch(
        "menuai.components.cert_expiry.helper.async_get_cert",
        side_effect=ssl.SSLError("some error"),
    ):
        entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state is not None
    assert state.state != STATE_UNAVAILABLE
    assert state.attributes.get("error") == "some error"
    assert not state.attributes.get("is_valid")


async def test_update_sensor(menuai: menuai) -> None:
    """Test async_update for sensor."""
    assert menuai.state is CoreState.running

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PORT: PORT},
        unique_id=f"{HOST}:{PORT}",
    )

    starting_time = static_datetime()
    timestamp = future_timestamp(100)

    with (
        freeze_time(starting_time),
        patch(
            "menuai.components.cert_expiry.coordinator.get_cert_expiry_timestamp",
            return_value=timestamp,
        ),
    ):
        entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state is not None
    assert state.state != STATE_UNAVAILABLE
    assert state.state == timestamp.isoformat()
    assert state.attributes.get("error") == "None"
    assert state.attributes.get("is_valid")

    next_update = starting_time + timedelta(hours=24)
    with (
        freeze_time(next_update),
        patch(
            "menuai.components.cert_expiry.coordinator.get_cert_expiry_timestamp",
            return_value=timestamp,
        ),
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=24))
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state is not None
    assert state.state != STATE_UNAVAILABLE
    assert state.state == timestamp.isoformat()
    assert state.attributes.get("error") == "None"
    assert state.attributes.get("is_valid")


async def test_update_sensor_network_errors(menuai: menuai) -> None:
    """Test async_update for sensor."""
    assert menuai.state is CoreState.running

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST, CONF_PORT: PORT},
        unique_id=f"{HOST}:{PORT}",
    )

    starting_time = static_datetime()
    timestamp = future_timestamp(100)

    with (
        freeze_time(starting_time),
        patch(
            "menuai.components.cert_expiry.coordinator.get_cert_expiry_timestamp",
            return_value=timestamp,
        ),
    ):
        entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state is not None
    assert state.state != STATE_UNAVAILABLE
    assert state.state == timestamp.isoformat()
    assert state.attributes.get("error") == "None"
    assert state.attributes.get("is_valid")

    next_update = starting_time + timedelta(hours=24)

    with (
        freeze_time(next_update),
        patch(
            "menuai.components.cert_expiry.helper.async_get_cert",
            side_effect=socket.gaierror,
        ),
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=24))
        await menuai.async_block_till_done()

    next_update = starting_time + timedelta(hours=48)

    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state.state == STATE_UNAVAILABLE

    with (
        freeze_time(next_update),
        patch(
            "menuai.components.cert_expiry.coordinator.get_cert_expiry_timestamp",
            return_value=timestamp,
        ),
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=48))
        await menuai.async_block_till_done()

        state = menuai.states.get("sensor.example_com_cert_expiry")
        assert state is not None
        assert state.state != STATE_UNAVAILABLE
        assert state.state == timestamp.isoformat()
        assert state.attributes.get("error") == "None"
        assert state.attributes.get("is_valid")

    next_update = starting_time + timedelta(hours=72)

    with (
        freeze_time(next_update),
        patch(
            "menuai.components.cert_expiry.helper.async_get_cert",
            side_effect=ssl.SSLError("something bad"),
        ),
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=72))
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state is not None
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get("error") == "something bad"
    assert not state.attributes.get("is_valid")

    next_update = starting_time + timedelta(hours=96)

    with (
        freeze_time(next_update),
        patch(
            "menuai.components.cert_expiry.helper.async_get_cert",
            side_effect=Exception(),
        ),
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=96))
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.example_com_cert_expiry")
    assert state.state == STATE_UNAVAILABLE
