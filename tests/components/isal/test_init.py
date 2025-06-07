"""Test the Intelligent Storage Acceleration setup."""

from menuai.components.isal import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_setup(menuai: menuai) -> None:
    """Ensure we can setup."""
    assert await async_setup_component(menuai, DOMAIN, {})
