"""Fixtures for the Sensibo integration."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pysensibo import SensiboClient, SensiboData
import pytest

from menuai.components.sensibo.const import DOMAIN, PLATFORMS
from menuai.const import Platform
from menuai.core import menuai

from . import ENTRY_CONFIG

from tests.common import MockConfigEntry, load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "menuai.components.sensibo.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture(name="load_platforms")
async def patch_platform_constant() -> list[Platform]:
    """Return list of platforms to load."""
    return PLATFORMS


@pytest.fixture
async def load_int(
    menuai: menuai,
    mock_client: SensiboClient,
    load_platforms: list[Platform],
) -> MockConfigEntry:
    """Set up the Sensibo integration."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_CONFIG,
        entry_id="1",
        unique_id="firstnamelastname",
        version=2,
    )

    config_entry.add_to_menuai(menuai)

    with patch("menuai.components.sensibo.PLATFORMS", load_platforms):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    return config_entry


@pytest.fixture(name="mock_client")
async def get_client(
    menuai: menuai,
    get_data: tuple[SensiboData, dict[str, Any], dict[str, Any]],
) -> AsyncGenerator[MagicMock]:
    """Mock SensiboClient."""

    with (
        patch(
            "menuai.components.sensibo.coordinator.SensiboClient",
            autospec=True,
        ) as mock_client,
        patch("menuai.components.sensibo.util.SensiboClient", new=mock_client),
    ):
        client = mock_client.return_value
        client.async_get_devices_data.return_value = get_data[0]
        client.async_get_me.return_value = get_data[1]
        client.async_get_devices.return_value = get_data[2]
        yield client


@pytest.fixture(name="get_data")
async def get_data_from_library(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    load_json: tuple[dict[str, Any], dict[str, Any]],
) -> AsyncGenerator[tuple[SensiboData, dict[str, Any], dict[str, Any]]]:
    """Get data from api."""
    client = SensiboClient("1234567890", aioclient_mock.create_session(menuai.loop))
    with patch.object(
        client,
        "async_get_me",
        return_value=load_json[1],
    ):
        me = await client.async_get_me()
    with patch.object(
        client,
        "async_get_devices",
        return_value=load_json[0],
    ):
        data = await client.async_get_devices_data()
        raw_data = await client.async_get_devices()
    yield (data, me, raw_data)
    await client._session.close()


@pytest.fixture(name="load_json")
def load_json_from_fixture(
    load_data: tuple[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load fixture with json data and return."""
    json_data: dict[str, Any] = json.loads(load_data[0])
    json_me: dict[str, Any] = json.loads(load_data[1])
    return (json_data, json_me)


@pytest.fixture(name="load_data", scope="package")
def load_data_from_fixture() -> tuple[str, str]:
    """Load fixture with fixture data and return."""
    return (load_fixture("data.json", "sensibo"), load_fixture("me.json", "sensibo"))
