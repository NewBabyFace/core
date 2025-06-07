"""The tests for the Roku remote platform."""

from unittest.mock import MagicMock

from menuai.components.remote import (
    ATTR_COMMAND,
    DOMAIN as REMOTE_DOMAIN,
    SERVICE_SEND_COMMAND,
)
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import UPNP_SERIAL

from tests.common import MockConfigEntry

MAIN_ENTITY_ID = f"{REMOTE_DOMAIN}.my_roku_3"


async def test_setup(menuai: menuai, init_integration: MockConfigEntry) -> None:
    """Test setup with basic config."""
    assert menuai.states.get(MAIN_ENTITY_ID)


async def test_unique_id(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test unique id."""
    main = entity_registry.async_get(MAIN_ENTITY_ID)
    assert main.unique_id == UPNP_SERIAL


async def test_main_services(
    menuai: menuai,
    init_integration: MockConfigEntry,
    mock_roku: MagicMock,
) -> None:
    """Test platform services."""
    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: MAIN_ENTITY_ID},
        blocking=True,
    )
    assert mock_roku.remote.call_count == 1
    mock_roku.remote.assert_called_with("poweroff")

    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: MAIN_ENTITY_ID},
        blocking=True,
    )
    assert mock_roku.remote.call_count == 2
    mock_roku.remote.assert_called_with("poweron")

    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_SEND_COMMAND,
        {ATTR_ENTITY_ID: MAIN_ENTITY_ID, ATTR_COMMAND: ["home"]},
        blocking=True,
    )
    assert mock_roku.remote.call_count == 3
    mock_roku.remote.assert_called_with("home")
