"""Test the my init."""

from unittest import mock

from menuai.components.my import URL_PATH
from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_setup(menuai: menuai) -> None:
    """Test setup."""
    with mock.patch(
        "menuai.components.frontend.async_register_built_in_panel"
    ) as mock_register_panel:
        assert await async_setup_component(menuai, "my", {"foo": "bar"})
        assert mock_register_panel.call_args == mock.call(
            menuai, "my", frontend_url_path=URL_PATH
        )
