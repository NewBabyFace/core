"""Tests for the youless component."""

import requests_mock

from menuai.components import youless
from menuai.const import CONF_DEVICE, CONF_HOST
from menuai.core import menuai

from tests.common import (
    MockConfigEntry,
    async_load_json_array_fixture,
    async_load_json_object_fixture,
)


async def init_component(menuai: menuai) -> MockConfigEntry:
    """Check if the setup of the integration succeeds."""
    with requests_mock.Mocker() as mock:
        mock.get(
            "http://1.1.1.1/d",
            json=await async_load_json_object_fixture(
                menuai, "device.json", youless.DOMAIN
            ),
        )
        mock.get(
            "http://1.1.1.1/e",
            json=await async_load_json_array_fixture(
                menuai, "enologic.json", youless.DOMAIN
            ),
            headers={"Content-Type": "application/json"},
        )
        mock.get(
            "http://1.1.1.1/f",
            json=await async_load_json_object_fixture(
                menuai, "phase.json", youless.DOMAIN
            ),
            headers={"Content-Type": "application/json"},
        )

        entry = MockConfigEntry(
            domain=youless.DOMAIN,
            title="localhost",
            data={CONF_HOST: "1.1.1.1", CONF_DEVICE: "localhost"},
        )
        entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    return entry
