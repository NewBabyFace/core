"""The tests for the Netatmo climate platform."""

from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    CONF_WEBHOOK_ID,
    SERVICE_SELECT_OPTION,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import selected_platforms, simulate_webhook, snapshot_platform_entities

from tests.common import MockConfigEntry


async def test_entity(
    menuai: menuai,
    config_entry: MockConfigEntry,
    netatmo_auth: AsyncMock,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test entities."""
    await snapshot_platform_entities(
        menuai,
        config_entry,
        Platform.SELECT,
        entity_registry,
        snapshot,
    )


async def test_select_schedule_thermostats(
    menuai: menuai,
    config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
    netatmo_auth: AsyncMock,
) -> None:
    """Test service for selecting Netatmo schedule with thermostats."""
    with selected_platforms(["climate", "select"]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)

        await menuai.async_block_till_done()

    webhook_id = config_entry.data[CONF_WEBHOOK_ID]
    select_entity = "select.myhome"

    assert menuai.states.get(select_entity).state == "Default"

    # Fake backend response changing schedule
    response = {
        "event_type": "schedule",
        "schedule_id": "b1b54a2f45795764f59d50d8",
        "previous_schedule_id": "59d32176d183948b05ab4dce",
        "push_type": "home_event_changed",
    }
    await simulate_webhook(menuai, webhook_id, response)
    await menuai.async_block_till_done()

    assert menuai.states.get(select_entity).state == "Winter"
    assert menuai.states.get(select_entity).attributes[ATTR_OPTIONS] == [
        "Default",
        "Winter",
    ]

    # Test setting a different schedule
    with patch("pyatmo.home.Home.async_switch_schedule") as mock_switch_home_schedule:
        await menuai.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: select_entity,
                ATTR_OPTION: "Default",
            },
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_switch_home_schedule.assert_called_once_with(
            schedule_id="591b54a2764ff4d50d8b5795"
        )

    # Fake backend response changing schedule
    response = {
        "event_type": "schedule",
        "schedule_id": "591b54a2764ff4d50d8b5795",
        "previous_schedule_id": "b1b54a2f45795764f59d50d8",
        "push_type": "home_event_changed",
    }
    await simulate_webhook(menuai, webhook_id, response)

    assert menuai.states.get(select_entity).state == "Default"
