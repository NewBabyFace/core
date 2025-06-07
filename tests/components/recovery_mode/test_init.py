"""Tests for the Recovery Mode integration."""

from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import async_get_persistent_notifications


async def test_works(menuai: menuai) -> None:
    """Test Recovery Mode works."""
    assert await async_setup_component(menuai, "recovery_mode", {})
    await menuai.async_block_till_done()
    notifications = async_get_persistent_notifications(menuai)
    assert len(notifications) == 1
