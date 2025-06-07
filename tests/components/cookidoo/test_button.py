"""Tests for the Cookidoo button platform."""

from unittest.mock import AsyncMock, patch

from cookidoo_api import CookidooRequestException
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_cookidoo_client: AsyncMock,
    cookidoo_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.cookidoo.PLATFORMS", [Platform.BUTTON]):
        await setup_integration(menuai, cookidoo_config_entry)

    assert cookidoo_config_entry.state is ConfigEntryState.LOADED

    await snapshot_platform(
        menuai, entity_registry, snapshot, cookidoo_config_entry.entry_id
    )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_pressing_button(
    menuai: menuai,
    mock_cookidoo_client: AsyncMock,
    cookidoo_config_entry: MockConfigEntry,
) -> None:
    """Test pressing button."""
    await setup_integration(menuai, cookidoo_config_entry)

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {
            ATTR_ENTITY_ID: "button.cookidoo_clear_shopping_list_and_additional_purchases",
        },
        blocking=True,
    )
    mock_cookidoo_client.clear_shopping_list.assert_called_once()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_pressing_button_exception(
    menuai: menuai,
    mock_cookidoo_client: AsyncMock,
    cookidoo_config_entry: MockConfigEntry,
) -> None:
    """Test pressing button with exception."""

    await setup_integration(menuai, cookidoo_config_entry)

    assert cookidoo_config_entry.state is ConfigEntryState.LOADED

    mock_cookidoo_client.clear_shopping_list.side_effect = CookidooRequestException
    with pytest.raises(
        menuaiError,
        match="Failed to clear all items from the Cookidoo shopping list",
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.cookidoo_clear_shopping_list_and_additional_purchases",
            },
            blocking=True,
        )
