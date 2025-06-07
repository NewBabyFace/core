"""Test the IKEA Idasen Desk connection buttons."""

from unittest.mock import MagicMock

from menuai.core import menuai

from . import init_integration


async def test_connect_button(
    menuai: menuai,
    mock_desk_api: MagicMock,
) -> None:
    """Test pressing the connect button."""
    await init_integration(menuai)

    await menuai.services.async_call(
        "button", "press", {"entity_id": "button.test_connect"}, blocking=True
    )
    assert mock_desk_api.connect.call_count == 2


async def test_disconnect_button(
    menuai: menuai,
    mock_desk_api: MagicMock,
) -> None:
    """Test pressing the disconnect button."""
    await init_integration(menuai)
    mock_desk_api.is_connected = True

    await menuai.services.async_call(
        "button", "press", {"entity_id": "button.test_disconnect"}, blocking=True
    )
    mock_desk_api.disconnect.assert_called_once()
