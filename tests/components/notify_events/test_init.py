"""The tests for notify_events."""

from menuai.components.notify_events.const import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_setup(menuai: menuai) -> None:
    """Test setup of the integration."""
    config = {"notify_events": {"token": "ABC"}}
    assert await async_setup_component(menuai, DOMAIN, config)
    await menuai.async_block_till_done()

    assert DOMAIN in menuai.data
