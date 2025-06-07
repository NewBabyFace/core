"""Tests for the squeezebox button component."""

from unittest.mock import MagicMock

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai


async def test_squeezebox_press(
    menuai: menuai, configured_player_with_button: MagicMock
) -> None:
    """Test press service call."""
    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.test_player_preset_1"},
        blocking=True,
    )

    configured_player_with_button.async_query.assert_called_with(
        "button", "preset_1.single"
    )
