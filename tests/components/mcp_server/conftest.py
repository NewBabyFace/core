"""Common fixtures for the Model Context Protocol Server tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from menuai.components.mcp_server.const import DOMAIN
from menuai.const import CONF_LLM_menuai_API
from menuai.core import menuai
from menuai.helpers import llm

from tests.common import MockConfigEntry


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "menuai.components.mcp_server.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture(name="llm_menuai_api")
def llm_menuai_api_fixture() -> str:
    """Fixture for the config entry llm_menuai_api."""
    return llm.LLM_API_ASSIST


@pytest.fixture(name="config_entry")
def mock_config_entry(menuai: menuai, llm_menuai_api: str) -> MockConfigEntry:
    """Fixture to load the integration."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_LLM_menuai_API: llm_menuai_api,
        },
    )
    config_entry.add_to_menuai(menuai)
    return config_entry
