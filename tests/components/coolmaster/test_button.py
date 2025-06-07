"""The test for the Coolmaster button platform."""

from __future__ import annotations

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.config_entries import ConfigEntry
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai


async def test_button(
    menuai: menuai,
    load_int: ConfigEntry,
) -> None:
    """Test the Coolmaster button."""
    assert menuai.states.get("binary_sensor.l1_101_clean_filter").state == "on"

    button = menuai.states.get("button.l1_101_reset_filter")
    assert button is not None
    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {
            ATTR_ENTITY_ID: button.entity_id,
        },
        blocking=True,
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.l1_101_clean_filter").state == "off"
