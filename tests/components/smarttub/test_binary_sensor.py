"""Test the SmartTub binary sensor platform."""

from datetime import datetime
from unittest.mock import create_autospec

import pytest
import smarttub

from menuai.components.binary_sensor import STATE_OFF, STATE_ON
from menuai.core import menuai


async def test_binary_sensors(spa, setup_entry, menuai: menuai) -> None:
    """Test simple binary sensors."""

    entity_id = f"binary_sensor.{spa.brand}_{spa.model}_online"
    state = menuai.states.get(entity_id)
    # disabled by default
    assert state is None

    entity_id = f"binary_sensor.{spa.brand}_{spa.model}_error"
    state = menuai.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_OFF


async def test_reminders(spa, setup_entry, menuai: menuai) -> None:
    """Test the reminder sensor."""

    entity_id = f"binary_sensor.{spa.brand}_{spa.model}_myfilter_reminder"
    state = menuai.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_OFF
    assert state.attributes["snoozed"] is False
    assert state.attributes["days"] == 2


@pytest.fixture
def mock_error(spa):
    """Mock error."""
    error = create_autospec(smarttub.SpaError, instance=True)
    error.code = 11
    error.title = "Flow Switch Stuck Open"
    error.description = None
    error.active = True
    error.created_at = datetime.now()
    error.updated_at = datetime.now()
    error.error_type = "TUB_ERROR"
    return error


async def test_error(spa, menuai: menuai, config_entry, mock_error) -> None:
    """Test the error sensor."""

    spa.get_errors.return_value = [mock_error]

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    entity_id = f"binary_sensor.{spa.brand}_{spa.model}_error"
    state = menuai.states.get(entity_id)
    assert state is not None

    assert state.state == STATE_ON
    assert state.attributes["error_code"] == 11


async def test_snooze_reminder(spa, setup_entry, menuai: menuai) -> None:
    """Test snoozing a reminder."""

    entity_id = f"binary_sensor.{spa.brand}_{spa.model}_myfilter_reminder"
    reminder = spa.get_reminders.return_value[0]
    days = 30

    await menuai.services.async_call(
        "smarttub",
        "snooze_reminder",
        {
            "entity_id": entity_id,
            "days": days,
        },
        blocking=True,
    )

    reminder.snooze.assert_called_with(days)


async def test_reset_reminder(spa, setup_entry, menuai: menuai) -> None:
    """Test snoozing a reminder."""

    entity_id = f"binary_sensor.{spa.brand}_{spa.model}_myfilter_reminder"
    reminder = spa.get_reminders.return_value[0]
    days = 180

    await menuai.services.async_call(
        "smarttub",
        "reset_reminder",
        {
            "entity_id": entity_id,
            "days": days,
        },
        blocking=True,
    )

    reminder.reset.assert_called_with(days)
