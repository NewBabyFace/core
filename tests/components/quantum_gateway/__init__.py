"""Tests for the quantum_gateway component."""

from menuai.components.device_tracker import DOMAIN as DEVICE_TRACKER_DOMAIN
from menuai.const import CONF_PASSWORD, CONF_PLATFORM
from menuai.core import menuai
from menuai.setup import async_setup_component


async def setup_platform(menuai: menuai) -> None:
    """Set up the quantum_gateway integration."""
    result = await async_setup_component(
        menuai,
        DEVICE_TRACKER_DOMAIN,
        {
            DEVICE_TRACKER_DOMAIN: {
                CONF_PLATFORM: "quantum_gateway",
                CONF_PASSWORD: "fake_password",
            }
        },
    )
    await menuai.async_block_till_done()
    assert result
