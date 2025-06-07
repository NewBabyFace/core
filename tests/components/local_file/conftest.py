"""Fixtures for the Local file integration."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from menuai.components.local_file.const import DEFAULT_NAME, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_FILE_PATH, CONF_NAME
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Automatically patch setup."""
    with patch(
        "menuai.components.local_file.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture(name="get_config")
async def get_config_to_integration_load() -> dict[str, Any]:
    """Return configuration.

    To override the config, tests can be marked with:
    @pytest.mark.parametrize("get_config", [{...}])
    """
    return {CONF_NAME: DEFAULT_NAME, CONF_FILE_PATH: "mock.file"}


@pytest.fixture(name="loaded_entry")
async def load_integration(
    menuai: menuai, get_config: dict[str, Any]
) -> MockConfigEntry:
    """Set up the Local file integration in MenuAI."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        options=get_config,
        entry_id="1",
    )

    config_entry.add_to_menuai(menuai)
    with (
        patch("os.path.isfile", Mock(return_value=True)),
        patch("os.access", Mock(return_value=True)),
        patch(
            "menuai.components.local_file.camera.mimetypes.guess_type",
            Mock(return_value=(None, None)),
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    return config_entry
