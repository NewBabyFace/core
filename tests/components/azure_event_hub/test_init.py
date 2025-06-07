"""Test the init functions for AEH."""

from datetime import timedelta
import logging
from unittest.mock import AsyncMock, MagicMock, patch

from azure.eventhub.exceptions import EventHubError
import pytest

from menuai.components import azure_event_hub
from menuai.components.azure_event_hub.const import CONF_SEND_INTERVAL, DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_ON
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util.dt import utcnow

from .conftest import FilterTest
from .const import AZURE_EVENT_HUB_PATH, BASIC_OPTIONS, CS_CONFIG_FULL, SAS_CONFIG_FULL

from tests.common import MockConfigEntry, async_fire_time_changed

_LOGGER = logging.getLogger(__name__)


async def test_import(menuai: menuai) -> None:
    """Test the popping of the filter and further import of the config."""
    config = {
        DOMAIN: {
            "send_interval": 10,
            "max_delay": 10,
            "filter": {
                "include_domains": ["light"],
                "include_entity_globs": ["sensor.included_*"],
                "include_entities": ["binary_sensor.included"],
                "exclude_domains": ["light"],
                "exclude_entity_globs": ["sensor.excluded_*"],
                "exclude_entities": ["binary_sensor.excluded"],
            },
        }
    }
    config[DOMAIN].update(CS_CONFIG_FULL)
    assert await async_setup_component(menuai, DOMAIN, config)


async def test_filter_only_config(menuai: menuai) -> None:
    """Test the popping of the filter and further import of the config."""
    config = {
        DOMAIN: {
            "filter": {
                "include_domains": ["light"],
                "include_entity_globs": ["sensor.included_*"],
                "include_entities": ["binary_sensor.included"],
                "exclude_domains": ["light"],
                "exclude_entity_globs": ["sensor.excluded_*"],
                "exclude_entities": ["binary_sensor.excluded"],
            },
        }
    }
    assert await async_setup_component(menuai, DOMAIN, config)


async def test_unload_entry(
    menuai: menuai, entry: MockConfigEntry, mock_create_batch: MagicMock
) -> None:
    """Test being able to unload an entry.

    Queue should be empty, so adding events to the batch should not be called,
    this verifies that the unload, calls async_stop, which calls async_send and
    shuts down the hub.
    """
    assert await menuai.config_entries.async_unload(entry.entry_id)
    mock_create_batch.add.assert_not_called()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_failed_test_connection(
    menuai: menuai, mock_get_eventhub_properties: AsyncMock
) -> None:
    """Test being able to unload an entry."""
    entry = MockConfigEntry(
        domain=azure_event_hub.DOMAIN,
        data=SAS_CONFIG_FULL,
        title="test-instance",
        options=BASIC_OPTIONS,
    )
    entry.add_to_menuai(menuai)
    mock_get_eventhub_properties.side_effect = EventHubError("Test")
    await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_send_batch_error(
    menuai: menuai,
    entry_with_one_event: MockConfigEntry,
    mock_send_batch: AsyncMock,
) -> None:
    """Test a error in send_batch, including recovering at the next interval."""
    mock_send_batch.reset_mock()
    mock_send_batch.side_effect = [EventHubError("Test"), None]
    async_fire_time_changed(
        menuai,
        utcnow() + timedelta(seconds=entry_with_one_event.options[CONF_SEND_INTERVAL]),
    )
    await menuai.async_block_till_done()
    mock_send_batch.assert_called_once()
    mock_send_batch.reset_mock()
    menuai.states.async_set("sensor.test2", STATE_ON)
    async_fire_time_changed(
        menuai,
        utcnow() + timedelta(seconds=entry_with_one_event.options[CONF_SEND_INTERVAL]),
    )
    await menuai.async_block_till_done()
    mock_send_batch.assert_called_once()
    mock_send_batch.side_effect = None  # Reset to avoid error in teardown


async def test_late_event(
    menuai: menuai,
    entry_with_one_event: MockConfigEntry,
    mock_create_batch: MagicMock,
) -> None:
    """Test the check on late events."""
    with patch(
        f"{AZURE_EVENT_HUB_PATH}.utcnow",
        return_value=utcnow() + timedelta(hours=1),
    ):
        async_fire_time_changed(
            menuai,
            utcnow()
            + timedelta(seconds=entry_with_one_event.options[CONF_SEND_INTERVAL]),
        )
        await menuai.async_block_till_done()
        mock_create_batch.add.assert_not_called()


async def test_full_batch(
    menuai: menuai,
    entry_with_one_event: MockConfigEntry,
    mock_create_batch: MagicMock,
) -> None:
    """Test the full batch behaviour."""
    mock_create_batch.add.side_effect = [ValueError, None]
    async_fire_time_changed(
        menuai,
        utcnow() + timedelta(seconds=entry_with_one_event.options[CONF_SEND_INTERVAL]),
    )
    await menuai.async_block_till_done()
    assert mock_create_batch.add.call_count == 2


@pytest.mark.parametrize(
    ("filter_schema", "tests"),
    [
        (
            {
                "include_domains": ["light"],
                "include_entity_globs": ["sensor.included_*"],
                "include_entities": ["binary_sensor.included"],
            },
            [
                FilterTest("climate.excluded", 0),
                FilterTest("light.included", 1),
                FilterTest("sensor.excluded_test", 0),
                FilterTest("sensor.included_test", 1),
                FilterTest("binary_sensor.included", 1),
                FilterTest("binary_sensor.excluded", 0),
            ],
        ),
        (
            {
                "exclude_domains": ["climate"],
                "exclude_entity_globs": ["sensor.excluded_*"],
                "exclude_entities": ["binary_sensor.excluded"],
            },
            [
                FilterTest("climate.excluded", 0),
                FilterTest("light.included", 1),
                FilterTest("sensor.excluded_test", 0),
                FilterTest("sensor.included_test", 1),
                FilterTest("binary_sensor.included", 1),
                FilterTest("binary_sensor.excluded", 0),
            ],
        ),
        (
            {
                "include_domains": ["light"],
                "include_entity_globs": ["*.included_*"],
                "exclude_domains": ["climate"],
                "exclude_entity_globs": ["*.excluded_*"],
                "exclude_entities": ["light.excluded"],
            },
            [
                FilterTest("light.included", 1),
                FilterTest("light.excluded_test", 0),
                FilterTest("light.excluded", 0),
                FilterTest("sensor.included_test", 1),
                FilterTest("climate.included_test", 1),
            ],
        ),
        (
            {
                "include_entities": ["climate.included", "sensor.excluded_test"],
                "exclude_domains": ["climate"],
                "exclude_entity_globs": ["*.excluded_*"],
                "exclude_entities": ["light.excluded"],
            },
            [
                FilterTest("climate.excluded", 0),
                FilterTest("climate.included", 1),
                FilterTest("switch.excluded_test", 0),
                FilterTest("sensor.excluded_test", 1),
                FilterTest("light.excluded", 0),
                FilterTest("light.included", 1),
            ],
        ),
    ],
    ids=["allowlist", "denylist", "filtered_allowlist", "filtered_denylist"],
)
async def test_filter(
    menuai: menuai,
    entry: MockConfigEntry,
    tests: list[FilterTest],
    mock_create_batch: MagicMock,
) -> None:
    """Test different filters.

    Filter_schema is also a fixture which is replaced by the filter_schema
    in the parametrize and added to the entry fixture.
    """
    for test in tests:
        menuai.states.async_set(test.entity_id, STATE_ON)
        async_fire_time_changed(
            menuai, utcnow() + timedelta(seconds=entry.options[CONF_SEND_INTERVAL])
        )
        await menuai.async_block_till_done()
        assert mock_create_batch.add.call_count == test.expected_count
        mock_create_batch.add.reset_mock()
