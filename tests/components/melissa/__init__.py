"""Tests for the melissa component."""

from menuai.core import menuai
from menuai.setup import async_setup_component

VALID_CONFIG = {"melissa": {"username": "********", "password": "********"}}


async def setup_integration(menuai: menuai) -> None:
    """Set up the melissa integration in MenuAI."""
    assert await async_setup_component(menuai, "melissa", VALID_CONFIG)
    await menuai.async_block_till_done()
