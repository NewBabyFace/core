"""The tests for nuki integration."""

import requests_mock

from menuai.components.nuki.const import DOMAIN
from menuai.core import menuai

from .mock import MOCK_INFO, setup_nuki_integration

from tests.common import (
    MockConfigEntry,
    async_load_json_array_fixture,
    async_load_json_object_fixture,
)


async def init_integration(menuai: menuai) -> MockConfigEntry:
    """Mock integration setup."""
    with requests_mock.Mocker() as mock:
        # Mocking authentication endpoint
        mock.get("http://1.1.1.1:8080/info", json=MOCK_INFO)
        mock.get(
            "http://1.1.1.1:8080/list",
            json=await async_load_json_array_fixture(menuai, "list.json", DOMAIN),
        )
        mock.get(
            "http://1.1.1.1:8080/callback/list",
            json=await async_load_json_object_fixture(
                menuai, "callback_list.json", DOMAIN
            ),
        )
        mock.get(
            "http://1.1.1.1:8080/callback/add",
            json=await async_load_json_object_fixture(
                menuai, "callback_add.json", DOMAIN
            ),
        )
        entry = await setup_nuki_integration(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
    return entry
