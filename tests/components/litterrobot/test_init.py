"""Test Litter-Robot setup process."""

from unittest.mock import MagicMock, patch

from pylitterbot.exceptions import LitterRobotException, LitterRobotLoginException
import pytest

from menuai.components.vacuum import (
    DOMAIN as VACUUM_DOMAIN,
    SERVICE_START,
    VacuumActivity,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component

from .common import CONFIG, DOMAIN, VACUUM_ENTITY_ID
from .conftest import setup_integration

from tests.common import MockConfigEntry
from tests.typing import WebSocketGenerator


async def test_unload_entry(menuai: menuai, mock_account: MagicMock) -> None:
    """Test being able to unload an entry."""
    entry = await setup_integration(menuai, mock_account, VACUUM_DOMAIN)

    vacuum = menuai.states.get(VACUUM_ENTITY_ID)
    assert vacuum
    assert vacuum.state == VacuumActivity.DOCKED

    await menuai.services.async_call(
        VACUUM_DOMAIN,
        SERVICE_START,
        {ATTR_ENTITY_ID: VACUUM_ENTITY_ID},
        blocking=True,
    )
    mock_account.robots[0].start_cleaning.assert_called_once()

    assert await menuai.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    ("side_effect", "expected_state"),
    [
        (LitterRobotLoginException, ConfigEntryState.SETUP_ERROR),
        (LitterRobotException, ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_entry_not_setup(
    menuai: menuai,
    side_effect: LitterRobotException,
    expected_state: ConfigEntryState,
) -> None:
    """Test being able to handle config entry not setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONFIG[DOMAIN],
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.litterrobot.coordinator.Account.connect",
        side_effect=side_effect,
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        assert entry.state is expected_state


async def test_device_remove_devices(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_account: MagicMock,
) -> None:
    """Test we can only remove a device that no longer exists."""
    assert await async_setup_component(menuai, "config", {})
    config_entry = await setup_integration(menuai, mock_account, VACUUM_DOMAIN)

    entity = entity_registry.entities[VACUUM_ENTITY_ID]
    assert entity.unique_id == "LR3C012345-litter_box"

    device_entry = device_registry.async_get(entity.device_id)
    client = await menuai_ws_client(menuai)
    response = await client.remove_device(device_entry.id, config_entry.entry_id)
    assert not response["success"]

    dead_device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, "test-serial", "remove-serial")},
    )
    response = await client.remove_device(dead_device_entry.id, config_entry.entry_id)
    assert response["success"]
