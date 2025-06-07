"""Test the Advantage Air Select Platform."""

from unittest.mock import AsyncMock

from menuai.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import add_mock_config


async def test_select_async_setup_entry(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_get: AsyncMock,
    mock_update: AsyncMock,
) -> None:
    """Test select platform."""

    await add_mock_config(menuai)

    # Test MyZone Select Entity
    entity_id = "select.myzone_myzone"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == "Zone open with Sensor"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-myzone"

    await menuai.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: "Zone 3"},
        blocking=True,
    )
    mock_update.assert_called_once()
