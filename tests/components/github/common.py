"""Common helpers for GitHub integration tests."""

from __future__ import annotations

import json

from menuai.components.github.const import CONF_REPOSITORIES, DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry, async_load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

MOCK_ACCESS_TOKEN = "gho_16C7e42F292c6912E7710c838347Ae178B4a"
TEST_REPOSITORY = "octocat/Hello-World"


async def setup_github_integration(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    add_entry_to_menuai: bool = True,
) -> None:
    """Mock setting up the integration."""
    headers = json.loads(await async_load_fixture(menuai, "base_headers.json", DOMAIN))
    for idx, repository in enumerate(mock_config_entry.options[CONF_REPOSITORIES]):
        aioclient_mock.get(
            f"https://api.github.com/repos/{repository}",
            json={
                **json.loads(await async_load_fixture(menuai, "repository.json", DOMAIN)),
                "full_name": repository,
                "id": idx,
            },
            headers=headers,
        )
        aioclient_mock.get(
            f"https://api.github.com/repos/{repository}/events",
            json=[],
            headers=headers,
        )
    aioclient_mock.post(
        "https://api.github.com/graphql",
        json=json.loads(await async_load_fixture(menuai, "graphql.json", DOMAIN)),
        headers=headers,
    )
    if add_entry_to_menuai:
        mock_config_entry.add_to_menuai(menuai)

    setup_result = await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert setup_result
    assert mock_config_entry.state is ConfigEntryState.LOADED
