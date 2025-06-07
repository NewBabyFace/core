"""Test sky_remote remote."""

import pytest

from menuai.components.remote import (
    ATTR_COMMAND,
    DOMAIN as REMOTE_DOMAIN,
    SERVICE_SEND_COMMAND,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError

from . import setup_mock_entry

ENTITY_ID = "remote.example_com"


async def test_send_command(
    menuai: menuai, mock_config_entry, mock_remote_control
) -> None:
    """Test "send_command" method."""
    await setup_mock_entry(menuai, mock_config_entry)
    await menuai.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_SEND_COMMAND,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_COMMAND: ["sky"]},
        blocking=True,
    )
    mock_remote_control._instance_mock.send_keys.assert_called_once_with(["sky"])


async def test_send_invalid_command(
    menuai: menuai, mock_config_entry, mock_remote_control
) -> None:
    """Test "send_command" method."""
    await setup_mock_entry(menuai, mock_config_entry)

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_SEND_COMMAND,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_COMMAND: ["apple"]},
            blocking=True,
        )
    mock_remote_control._instance_mock.send_keys.assert_not_called()
