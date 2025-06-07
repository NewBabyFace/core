"""Tests prosegur setup."""

from unittest.mock import patch

import pytest

from menuai.core import menuai

from tests.test_util.aiohttp import AiohttpClientMocker


@pytest.mark.parametrize(
    "error",
    [
        ConnectionRefusedError,
        ConnectionError,
    ],
)
async def test_setup_entry_fail_retrieve(
    menuai: menuai, mock_config_entry, error
) -> None:
    """Test loading the Prosegur entry."""

    mock_config_entry.add_to_menuai(menuai)

    with patch(
        "pyprosegur.auth.Auth.login",
        side_effect=error,
    ):
        assert not await menuai.config_entries.async_setup(mock_config_entry.entry_id)

        await menuai.async_block_till_done()


async def test_unload_entry(
    menuai: menuai,
    init_integration,
    mock_config_entry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test unloading the Prosegur entry."""

    assert await menuai.config_entries.async_unload(mock_config_entry.entry_id)
