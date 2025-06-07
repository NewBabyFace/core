"""Tests for JVC Projector remote platform."""

from unittest.mock import MagicMock

import pytest

from menuai.components.remote import (
    ATTR_COMMAND,
    DOMAIN as REMOTE_DOMAIN,
    SERVICE_SEND_COMMAND,
)
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry

ENTITY_ID = "remote.jvc_projector"


async def test_entity_state(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_device: MagicMock,
    mock_integration: MockConfigEntry,
) -> None:
    """Tests entity state is registered."""
    entity = menuai.states.get(ENTITY_ID)
    assert entity
    assert entity_registry.async_get(entity.entity_id)


async def test_commands(
    menuai: menuai,
    mock_device: MagicMock,
    mock_integration: MockConfigEntry,
) -> None:
    """Test service call are called."""
    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    assert mock_device.power_on.call_count == 1

    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    assert mock_device.power_off.call_count == 1

    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_SEND_COMMAND,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_COMMAND: ["ok"]},
        blocking=True,
    )
    assert mock_device.remote.call_count == 1

    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_SEND_COMMAND,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_COMMAND: ["hdmi_1"]},
        blocking=True,
    )
    assert mock_device.remote.call_count == 2


async def test_unknown_command(
    menuai: menuai,
    mock_device: MagicMock,
    mock_integration: MockConfigEntry,
) -> None:
    """Test unknown service call errors."""
    with pytest.raises(menuaiError) as err:
        await menuai.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_SEND_COMMAND,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_COMMAND: ["bad"]},
            blocking=True,
        )
    assert str(err.value) == "bad is not a known command"
