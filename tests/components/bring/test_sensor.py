"""Test for sensor platform of the Bring! integration."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

from bring_api import BringItemsResponse
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.bring.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, async_load_fixture, snapshot_platform


@pytest.fixture(autouse=True)
def sensor_only() -> Generator[None]:
    """Enable only the sensor platform."""
    with patch(
        "menuai.components.bring.PLATFORMS",
        [Platform.SENSOR],
    ):
        yield


async def test_setup(
    menuai: menuai,
    bring_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_bring_client: AsyncMock,
) -> None:
    """Snapshot test states of sensor platform."""

    mock_bring_client.get_list.side_effect = [
        BringItemsResponse.from_json(
            await async_load_fixture(menuai, "items.json", DOMAIN)
        ),
        BringItemsResponse.from_json(
            await async_load_fixture(menuai, "items2.json", DOMAIN)
        ),
    ]
    bring_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(bring_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert bring_config_entry.state is ConfigEntryState.LOADED

    await snapshot_platform(
        menuai, entity_registry, snapshot, bring_config_entry.entry_id
    )


@pytest.mark.parametrize(
    ("fixture", "entity_state"),
    [
        ("items_invitation", "invitation"),
        ("items_shared", "shared"),
        ("items", "registered"),
    ],
)
async def test_list_access_states(
    menuai: menuai,
    bring_config_entry: MockConfigEntry,
    mock_bring_client: AsyncMock,
    fixture: str,
    entity_state: str,
) -> None:
    """Snapshot test states of list access sensor."""

    mock_bring_client.get_list.return_value = BringItemsResponse.from_json(
        await async_load_fixture(menuai, f"{fixture}.json", DOMAIN)
    )
    bring_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(bring_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert bring_config_entry.state is ConfigEntryState.LOADED

    assert (state := menuai.states.get("sensor.einkauf_list_access"))
    assert state.state == entity_state
