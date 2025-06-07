"""Tests for the Anova integration."""

from __future__ import annotations

from unittest.mock import patch

from anova_wifi import APCUpdate, APCUpdateBinary, APCUpdateSensor

from menuai.components.anova.const import DOMAIN
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai

from tests.common import MockConfigEntry

DEVICE_UNIQUE_ID = "abc123def"

CONF_INPUT = {CONF_USERNAME: "sample@gmail.com", CONF_PASSWORD: "sample"}

ONLINE_UPDATE = APCUpdate(
    sensor=APCUpdateSensor(
        0, "Low water", "No state", 23.33, 0, "2.2.0", 20.87, 21.79, 21.33
    ),
    binary_sensor=APCUpdateBinary(False, False, False, True, False, True, False, False),
)


def create_entry(menuai: menuai, device_id: str = DEVICE_UNIQUE_ID) -> ConfigEntry:
    """Add config entry in MenuAI."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Anova",
        data={
            CONF_USERNAME: "sample@gmail.com",
            CONF_PASSWORD: "sample",
        },
        unique_id="sample@gmail.com",
        version=1,
        minor_version=2,
    )
    entry.add_to_menuai(menuai)
    return entry


async def async_init_integration(
    menuai: menuai,
    skip_setup: bool = False,
) -> ConfigEntry:
    """Set up the Anova integration in MenuAI."""

    with patch("menuai.components.anova.AnovaApi.authenticate"):
        entry = create_entry(menuai)

        if not skip_setup:
            await menuai.config_entries.async_setup(entry.entry_id)
            await menuai.async_block_till_done()

        return entry
