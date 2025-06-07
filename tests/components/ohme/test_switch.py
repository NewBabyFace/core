"""Tests for switches."""

from unittest.mock import AsyncMock, MagicMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_switches(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the Ohme switches."""
    with patch("menuai.components.ohme.PLATFORMS", [Platform.SWITCH]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_cap_switch_on(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the switch turn_on action."""
    await setup_integration(menuai, mock_config_entry)
    mock_client.async_change_price_cap = AsyncMock()

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "switch.ohme_home_pro_price_cap",
        },
        blocking=True,
    )

    mock_client.async_change_price_cap.assert_called_once_with(True)


async def test_cap_switch_off(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the switch turn_off action."""
    await setup_integration(menuai, mock_config_entry)
    mock_client.async_change_price_cap = AsyncMock()

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {
            ATTR_ENTITY_ID: "switch.ohme_home_pro_price_cap",
        },
        blocking=True,
    )

    mock_client.async_change_price_cap.assert_called_once_with(False)


async def test_config_switch_on(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the switch turn_on action."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "switch.ohme_home_pro_lock_buttons",
        },
        blocking=True,
    )

    assert len(mock_client.async_set_configuration_value.mock_calls) == 1


async def test_config_switch_off(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the switch turn_off action."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {
            ATTR_ENTITY_ID: "switch.ohme_home_pro_lock_buttons",
        },
        blocking=True,
    )

    assert len(mock_client.async_set_configuration_value.mock_calls) == 1
