"""The tests for the button component."""

from collections.abc import Generator
from unittest.mock import AsyncMock, call, patch

from pyloadapi import CannotConnect, InvalidAuth
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.components.pyload.button import PyLoadButtonEntity
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform

API_CALL = {
    PyLoadButtonEntity.ABORT_DOWNLOADS: call.stop_all_downloads,
    PyLoadButtonEntity.RESTART_FAILED: call.restart_failed,
    PyLoadButtonEntity.DELETE_FINISHED: call.delete_finished,
    PyLoadButtonEntity.RESTART: call.restart,
}


@pytest.fixture(autouse=True)
def button_only() -> Generator[None]:
    """Enable only the button platform."""
    with patch(
        "menuai.components.pyload.PLATFORMS",
        [Platform.BUTTON],
    ):
        yield


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_state(
    menuai: menuai,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_pyloadapi: AsyncMock,
) -> None:
    """Test button state."""

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_button_press(
    menuai: menuai,
    config_entry: MockConfigEntry,
    mock_pyloadapi: AsyncMock,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test button press method."""

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    for entity_entry in entity_entries:
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_entry.entity_id},
            blocking=True,
        )
        assert API_CALL[entity_entry.translation_key] in mock_pyloadapi.method_calls
        mock_pyloadapi.reset_mock()


@pytest.mark.parametrize(
    ("side_effect"),
    [CannotConnect, InvalidAuth],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_button_press_errors(
    menuai: menuai,
    config_entry: MockConfigEntry,
    mock_pyloadapi: AsyncMock,
    entity_registry: er.EntityRegistry,
    side_effect: Exception,
) -> None:
    """Test button press method."""

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )
    mock_pyloadapi.stop_all_downloads.side_effect = side_effect
    mock_pyloadapi.restart_failed.side_effect = side_effect
    mock_pyloadapi.delete_finished.side_effect = side_effect
    mock_pyloadapi.restart.side_effect = side_effect

    for entity_entry in entity_entries:
        with pytest.raises(ServiceValidationError):
            await menuai.services.async_call(
                BUTTON_DOMAIN,
                SERVICE_PRESS,
                {ATTR_ENTITY_ID: entity_entry.entity_id},
                blocking=True,
            )
