"""The tests for the litejet component."""

from menuai.components import litejet
from menuai.components.litejet.const import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import async_init_integration


async def test_setup_with_no_config(menuai: menuai) -> None:
    """Test that nothing happens."""
    assert await async_setup_component(menuai, DOMAIN, {}) is True
    assert DOMAIN not in menuai.data


async def test_unload_entry(menuai: menuai, mock_litejet) -> None:
    """Test being able to unload an entry."""
    entry = await async_init_integration(menuai, use_switch=True, use_scene=True)

    assert await litejet.async_unload_entry(menuai, entry)
    assert DOMAIN not in menuai.data
