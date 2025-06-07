"""Tests for Motionblinds BLE buttons."""

from unittest.mock import Mock

import pytest

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.components.motionblinds_ble.const import (
    ATTR_CONNECT,
    ATTR_DISCONNECT,
    ATTR_FAVORITE,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("motionblinds_ble_connect")
@pytest.mark.parametrize(
    ("button"),
    [
        ATTR_CONNECT,
        ATTR_DISCONNECT,
        ATTR_FAVORITE,
    ],
)
async def test_button(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_motion_device: Mock,
    name: str,
    button: str,
) -> None:
    """Test states of the button."""

    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: f"button.{name}_{button}"},
        blocking=True,
    )
    getattr(mock_motion_device, button).assert_called_once()
