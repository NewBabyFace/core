"""Diagnostics support for the GitHub integration."""

from __future__ import annotations

from typing import Any

from aiogithubapi import GitHubAPI, GitHubException

from menuai.const import CONF_ACCESS_TOKEN
from menuai.core import menuai
from menuai.helpers.aiohttp_client import (
    SERVER_SOFTWARE,
    async_get_clientsession,
)

from .coordinator import GithubConfigEntry


async def async_get_config_entry_diagnostics(
    menuai: menuai,
    config_entry: GithubConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = {"options": {**config_entry.options}}
    client = GitHubAPI(
        token=config_entry.data[CONF_ACCESS_TOKEN],
        session=async_get_clientsession(menuai),
        client_name=SERVER_SOFTWARE,
    )

    try:
        rate_limit_response = await client.rate_limit()
    except GitHubException as err:
        data["rate_limit"] = {"error": str(err)}
    else:
        data["rate_limit"] = rate_limit_response.data.as_dict

    repositories = config_entry.runtime_data
    data["repositories"] = {}

    for repository, coordinator in repositories.items():
        data["repositories"][repository] = coordinator.data

    return data
