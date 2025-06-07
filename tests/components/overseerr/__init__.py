"""Tests for the Overseerr integration."""

from typing import Any
from urllib.parse import urlparse

from aiohttp.test_utils import TestClient

from menuai.components.webhook import async_generate_url
from menuai.core import menuai

from .const import WEBHOOK_ID

from tests.common import MockConfigEntry


async def setup_integration(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()


async def call_webhook(
    menuai: menuai, data: dict[str, Any], client: TestClient
) -> None:
    """Call the webhook."""
    webhook_url = async_generate_url(menuai, WEBHOOK_ID)

    resp = await client.post(
        urlparse(webhook_url).path,
        json=data,
    )

    # Wait for remaining tasks to complete.
    await menuai.async_block_till_done()

    data = await resp.json()
    resp.close()
