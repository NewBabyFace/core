"""Tests for the Cloudflare integration."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pycfdns

from menuai.components.cloudflare.const import CONF_RECORDS, DOMAIN
from menuai.const import CONF_API_TOKEN, CONF_ZONE
from menuai.core import menuai
from menuai.helpers.typing import UNDEFINED, UndefinedType

from tests.common import MockConfigEntry

ENTRY_CONFIG = {
    CONF_API_TOKEN: "mock-api-token",
    CONF_ZONE: "mock.com",
    CONF_RECORDS: ["ha.mock.com", "menuai.mock.com"],
}

ENTRY_OPTIONS = {}

USER_INPUT = {
    CONF_API_TOKEN: "mock-api-token",
}

USER_INPUT_ZONE = {CONF_ZONE: "mock.com"}

USER_INPUT_RECORDS = {CONF_RECORDS: ["ha.mock.com", "menuai.mock.com"]}

MOCK_ZONE: pycfdns.ZoneModel = {"name": "mock.com", "id": "mock-zone-id"}
MOCK_ZONE_RECORDS: list[pycfdns.RecordModel] = [
    {
        "id": "zone-record-id",
        "type": "A",
        "name": "ha.mock.com",
        "proxied": True,
        "content": "127.0.0.1",
    },
    {
        "id": "zone-record-id-2",
        "type": "A",
        "name": "menuai.mock.com",
        "proxied": True,
        "content": "127.0.0.1",
    },
    {
        "id": "zone-record-id-3",
        "type": "A",
        "name": "mock.com",
        "proxied": True,
        "content": "127.0.0.1",
    },
]


async def init_integration(
    menuai: menuai,
    *,
    data: dict[str, Any] | UndefinedType = UNDEFINED,
    options: dict[str, Any] | UndefinedType = UNDEFINED,
    unique_id: str = MOCK_ZONE["name"],
    skip_setup: bool = False,
) -> MockConfigEntry:
    """Set up the Cloudflare integration in MenuAI."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_CONFIG if data is UNDEFINED else data,
        options=ENTRY_OPTIONS if options is UNDEFINED else options,
        unique_id=unique_id,
    )
    entry.add_to_menuai(menuai)

    if not skip_setup:
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    return entry


def get_mock_client() -> Mock:
    """Return of Mock of pycfdns.Client."""
    client = Mock()

    client.list_zones = AsyncMock(return_value=[MOCK_ZONE])
    client.list_dns_records = AsyncMock(return_value=MOCK_ZONE_RECORDS)
    client.update_dns_record = AsyncMock(return_value=None)

    return client


def patch_async_setup_entry() -> AsyncMock:
    """Patch the async_setup_entry method and return a mock."""
    return patch(
        "menuai.components.cloudflare.async_setup_entry",
        return_value=True,
    )
