"""Tests for Lovelace system health."""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from menuai.components.lovelace import dashboard
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import get_system_health_info


@pytest.fixture(autouse=True)
def mock_onboarding_done() -> Generator[MagicMock]:
    """Mock that MenuAI is currently onboarding.

    Enabled to prevent creating default dashboards during test execution.
    """
    with patch(
        "menuai.components.onboarding.async_is_onboarded",
        return_value=True,
    ) as mock_onboarding:
        yield mock_onboarding


async def test_system_health_info_autogen(menuai: menuai) -> None:
    """Test system health info endpoint."""
    assert await async_setup_component(menuai, "lovelace", {})
    assert await async_setup_component(menuai, "system_health", {})
    info = await get_system_health_info(menuai, "lovelace")
    assert info == {"dashboards": 1, "mode": "auto-gen", "resources": 0}


async def test_system_health_info_storage(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test system health info endpoint."""
    assert await async_setup_component(menuai, "system_health", {})
    menuai_storage[dashboard.CONFIG_STORAGE_KEY_DEFAULT] = {
        "key": "lovelace",
        "version": 1,
        "data": {"config": {"resources": [], "views": []}},
    }
    assert await async_setup_component(menuai, "lovelace", {})
    await menuai.async_block_till_done()
    info = await get_system_health_info(menuai, "lovelace")
    assert info == {"dashboards": 1, "mode": "storage", "resources": 0, "views": 0}


async def test_system_health_info_yaml(menuai: menuai) -> None:
    """Test system health info endpoint."""
    assert await async_setup_component(menuai, "system_health", {})
    assert await async_setup_component(menuai, "lovelace", {"lovelace": {"mode": "YAML"}})
    await menuai.async_block_till_done()
    with patch(
        "menuai.components.lovelace.dashboard.load_yaml_dict",
        return_value={"views": [{"cards": []}]},
    ):
        info = await get_system_health_info(menuai, "lovelace")
    assert info == {"dashboards": 1, "mode": "yaml", "resources": 0, "views": 1}


async def test_system_health_info_yaml_not_found(menuai: menuai) -> None:
    """Test system health info endpoint."""
    assert await async_setup_component(menuai, "system_health", {})
    assert await async_setup_component(menuai, "lovelace", {"lovelace": {"mode": "YAML"}})
    await menuai.async_block_till_done()
    info = await get_system_health_info(menuai, "lovelace")
    assert info == {
        "dashboards": 1,
        "mode": "yaml",
        "error": f"{menuai.config.path('ui-lovelace.yaml')} not found",
        "resources": 0,
    }
