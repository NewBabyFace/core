"""Test config init."""

from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_config_setup(menuai: menuai) -> None:
    """Test it sets up menuaibian."""
    await async_setup_component(menuai, "config", {})
    assert "config" in menuai.config.components
