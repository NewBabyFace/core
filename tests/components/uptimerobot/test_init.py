"""Test the UptimeRobot init."""

from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from pyuptimerobot import UptimeRobotAuthenticationException, UptimeRobotException

from menuai import config_entries
from menuai.components.uptimerobot.const import (
    COORDINATOR_UPDATE_INTERVAL,
    DOMAIN,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_ON, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .common import (
    MOCK_UPTIMEROBOT_CONFIG_ENTRY_DATA,
    MOCK_UPTIMEROBOT_CONFIG_ENTRY_DATA_KEY_READ_ONLY,
    MOCK_UPTIMEROBOT_MONITOR,
    UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY,
    MockApiResponseKey,
    mock_uptimerobot_api_response,
    setup_uptimerobot_integration,
)

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_reauthentication_trigger_in_setup(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test reauthentication trigger."""
    mock_config_entry = MockConfigEntry(**MOCK_UPTIMEROBOT_CONFIG_ENTRY_DATA)
    mock_config_entry.add_to_menuai(menuai)

    with patch(
        "pyuptimerobot.UptimeRobot.async_get_monitors",
        side_effect=UptimeRobotAuthenticationException,
    ):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

    flows = menuai.config_entries.flow.async_progress()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    assert mock_config_entry.reason == "could not authenticate"

    assert len(flows) == 1
    flow = flows[0]
    assert flow["step_id"] == "reauth_confirm"
    assert flow["handler"] == DOMAIN
    assert flow["context"]["source"] == config_entries.SOURCE_REAUTH
    assert flow["context"]["entry_id"] == mock_config_entry.entry_id

    assert (
        "Config entry 'test@test.test' for uptimerobot integration could not authenticate"
        in caplog.text
    )


async def test_reauthentication_trigger_key_read_only(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test reauthentication trigger."""
    mock_config_entry = MockConfigEntry(
        **MOCK_UPTIMEROBOT_CONFIG_ENTRY_DATA_KEY_READ_ONLY
    )
    mock_config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    flows = menuai.config_entries.flow.async_progress()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    assert (
        mock_config_entry.reason
        == "Wrong API key type detected, use the 'main' API key"
    )

    assert len(flows) == 1
    flow = flows[0]
    assert flow["step_id"] == "reauth_confirm"
    assert flow["handler"] == DOMAIN
    assert flow["context"]["source"] == config_entries.SOURCE_REAUTH
    assert flow["context"]["entry_id"] == mock_config_entry.entry_id

    assert (
        "Config entry 'test@test.test' for uptimerobot integration could not authenticate"
        in caplog.text
    )


async def test_reauthentication_trigger_after_setup(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test reauthentication trigger."""
    mock_config_entry = await setup_uptimerobot_integration(menuai)

    binary_sensor = menuai.states.get(UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY)
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert binary_sensor.state == STATE_ON

    with patch(
        "pyuptimerobot.UptimeRobot.async_get_monitors",
        side_effect=UptimeRobotAuthenticationException,
    ):
        freezer.tick(COORDINATOR_UPDATE_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    flows = menuai.config_entries.flow.async_progress()
    assert (
        menuai.states.get(UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY).state
        == STATE_UNAVAILABLE
    )

    assert "Authentication failed while fetching uptimerobot data" in caplog.text

    assert len(flows) == 1
    flow = flows[0]
    assert flow["step_id"] == "reauth_confirm"
    assert flow["handler"] == DOMAIN
    assert flow["context"]["source"] == config_entries.SOURCE_REAUTH
    assert flow["context"]["entry_id"] == mock_config_entry.entry_id


async def test_integration_reload(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test integration reload."""
    mock_entry = await setup_uptimerobot_integration(menuai)

    with patch(
        "pyuptimerobot.UptimeRobot.async_get_monitors",
        return_value=mock_uptimerobot_api_response(),
    ):
        assert await menuai.config_entries.async_reload(mock_entry.entry_id)
        freezer.tick(COORDINATOR_UPDATE_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    entry = menuai.config_entries.async_get_entry(mock_entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED
    assert menuai.states.get(UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY).state == STATE_ON


async def test_update_errors(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test errors during updates."""
    await setup_uptimerobot_integration(menuai)

    with patch(
        "pyuptimerobot.UptimeRobot.async_get_monitors",
        side_effect=UptimeRobotException,
    ):
        freezer.tick(COORDINATOR_UPDATE_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert (
            menuai.states.get(UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY).state
            == STATE_UNAVAILABLE
        )

    with patch(
        "pyuptimerobot.UptimeRobot.async_get_monitors",
        return_value=mock_uptimerobot_api_response(),
    ):
        freezer.tick(COORDINATOR_UPDATE_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert menuai.states.get(UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY).state == STATE_ON

    with patch(
        "pyuptimerobot.UptimeRobot.async_get_monitors",
        return_value=mock_uptimerobot_api_response(key=MockApiResponseKey.ERROR),
    ):
        freezer.tick(COORDINATOR_UPDATE_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert (
            menuai.states.get(UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY).state
            == STATE_UNAVAILABLE
        )

    assert "Error fetching uptimerobot data: test error from API" in caplog.text


async def test_device_management(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that we are adding and removing devices for monitors returned from the API."""
    mock_entry = await setup_uptimerobot_integration(menuai)

    devices = dr.async_entries_for_config_entry(device_registry, mock_entry.entry_id)
    assert len(devices) == 1

    assert devices[0].identifiers == {(DOMAIN, "1234")}
    assert devices[0].name == "Test monitor"

    assert menuai.states.get(UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY).state == STATE_ON
    assert menuai.states.get(f"{UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY}_2") is None

    with patch(
        "pyuptimerobot.UptimeRobot.async_get_monitors",
        return_value=mock_uptimerobot_api_response(
            data=[MOCK_UPTIMEROBOT_MONITOR, {**MOCK_UPTIMEROBOT_MONITOR, "id": 12345}]
        ),
    ):
        freezer.tick(COORDINATOR_UPDATE_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    devices = dr.async_entries_for_config_entry(device_registry, mock_entry.entry_id)
    assert len(devices) == 2
    assert devices[0].identifiers == {(DOMAIN, "1234")}
    assert devices[1].identifiers == {(DOMAIN, "12345")}

    assert menuai.states.get(UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY).state == STATE_ON
    assert (
        menuai.states.get(f"{UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY}_2").state == STATE_ON
    )

    with patch(
        "pyuptimerobot.UptimeRobot.async_get_monitors",
        return_value=mock_uptimerobot_api_response(),
    ):
        freezer.tick(COORDINATOR_UPDATE_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    devices = dr.async_entries_for_config_entry(device_registry, mock_entry.entry_id)
    assert len(devices) == 1
    assert devices[0].identifiers == {(DOMAIN, "1234")}

    assert menuai.states.get(UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY).state == STATE_ON
    assert menuai.states.get(f"{UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY}_2") is None
