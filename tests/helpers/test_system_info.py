"""Tests for the system info helper."""

import json
import os
from unittest.mock import patch

import pytest

from menuai.components import menuaiio
from menuai.const import __version__ as current_version
from menuai.core import menuai
from menuai.helpers.system_info import async_get_system_info


async def test_get_system_info(menuai: menuai) -> None:
    """Test the get system info."""
    info = await async_get_system_info(menuai)
    assert isinstance(info, dict)
    assert info["version"] == current_version
    assert info["user"] is not None
    assert json.dumps(info) is not None


async def test_get_system_info_supervisor_not_available(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the get system info when supervisor is not available."""
    menuai.config.components.add("menuaiio")
    with (
        patch("platform.system", return_value="Linux"),
        patch("menuai.helpers.system_info.is_docker_env", return_value=True),
        patch("menuai.helpers.system_info.is_official_image", return_value=True),
        patch.object(menuaiio, "is_menuaiio", return_value=True),
        patch.object(menuaiio, "get_info", return_value=None),
        patch("menuai.helpers.system_info.cached_get_user", return_value="root"),
    ):
        info = await async_get_system_info(menuai)
        assert isinstance(info, dict)
        assert info["version"] == current_version
        assert info["user"] is not None
        assert json.dumps(info) is not None
        assert info["installation_type"] == "MenuAI Supervised"
        assert "No MenuAI Supervisor info available" in caplog.text


async def test_get_system_info_supervisor_not_loaded(menuai: menuai) -> None:
    """Test the get system info when supervisor is not loaded."""
    with (
        patch("platform.system", return_value="Linux"),
        patch("menuai.helpers.system_info.is_docker_env", return_value=True),
        patch("menuai.helpers.system_info.is_official_image", return_value=True),
        patch.object(menuaiio, "get_info", return_value=None),
        patch.dict(os.environ, {"SUPERVISOR": "127.0.0.1"}),
    ):
        info = await async_get_system_info(menuai)
        assert isinstance(info, dict)
        assert info["version"] == current_version
        assert info["user"] is not None
        assert json.dumps(info) is not None
        assert info["installation_type"] == "Unsupported Third Party Container"


async def test_container_installationtype(menuai: menuai) -> None:
    """Test container installation type."""
    with (
        patch("platform.system", return_value="Linux"),
        patch("menuai.helpers.system_info.is_docker_env", return_value=True),
        patch("menuai.helpers.system_info.is_official_image", return_value=True),
        patch("menuai.helpers.system_info.cached_get_user", return_value="root"),
    ):
        info = await async_get_system_info(menuai)
        assert info["installation_type"] == "MenuAI Container"

    with (
        patch("platform.system", return_value="Linux"),
        patch("menuai.helpers.system_info.is_docker_env", return_value=True),
        patch(
            "menuai.helpers.system_info.is_official_image", return_value=False
        ),
        patch("menuai.helpers.system_info.cached_get_user", return_value="user"),
    ):
        info = await async_get_system_info(menuai)
        assert info["installation_type"] == "Unsupported Third Party Container"


@pytest.mark.parametrize("error", [KeyError, OSError])
async def test_getuser_oserror(menuai: menuai, error: Exception) -> None:
    """Test getuser oserror."""
    with patch("menuai.helpers.system_info.cached_get_user", side_effect=error):
        info = await async_get_system_info(menuai)
        assert info["user"] is None
