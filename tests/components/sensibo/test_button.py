"""The test for the sensibo button platform."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

from freezegun import freeze_time
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.config_entries import ConfigEntry
from menuai.const import (
    ATTR_ENTITY_ID,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed, snapshot_platform


@freeze_time("2022-03-12T15:24:26+00:00")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    "load_platforms",
    [[Platform.BUTTON]],
)
async def test_button(
    menuai: menuai,
    load_int: ConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Sensibo button."""

    await snapshot_platform(menuai, entity_registry, snapshot, load_int.entry_id)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    "load_platforms",
    [[Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]],
)
async def test_button_update(
    menuai: menuai,
    load_int: ConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the Sensibo button press."""

    state_button = menuai.states.get("button.hallway_reset_filter")
    state_filter_clean = menuai.states.get("binary_sensor.hallway_filter_clean_required")
    state_filter_last_reset = menuai.states.get("sensor.hallway_filter_last_reset")

    assert state_button.state is STATE_UNKNOWN
    assert state_filter_clean.state is STATE_ON
    assert state_filter_last_reset.state == "2022-03-12T15:24:26+00:00"

    today = dt_util.utcnow() + timedelta(minutes=10)
    today = today.replace(microsecond=0)
    today_str = today.isoformat(timespec="seconds")
    freezer.move_to(today)

    mock_client.async_reset_filter.return_value = {"status": "success"}

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {
            ATTR_ENTITY_ID: state_button.entity_id,
        },
        blocking=True,
    )

    mock_client.async_get_devices_data.return_value.parsed[
        "ABC999111"
    ].filter_clean = False
    mock_client.async_get_devices_data.return_value.parsed[
        "ABC999111"
    ].filter_last_reset = today

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state_button = menuai.states.get("button.hallway_reset_filter")
    state_filter_clean = menuai.states.get("binary_sensor.hallway_filter_clean_required")
    state_filter_last_reset = menuai.states.get("sensor.hallway_filter_last_reset")
    assert state_button.state == today_str
    assert state_filter_clean.state is STATE_OFF
    assert state_filter_last_reset.state == today_str


async def test_button_failure(
    menuai: menuai,
    load_int: ConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the Sensibo button failure."""

    state = menuai.states.get("button.hallway_reset_filter")

    mock_client.async_reset_filter.return_value = {"status": "failure"}

    with pytest.raises(
        menuaiError,
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: state.entity_id,
            },
            blocking=True,
        )
