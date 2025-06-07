"""Test Prusalink camera."""

from unittest.mock import patch

import pytest

from menuai.const import Platform
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.typing import ClientSessionGenerator


@pytest.fixture(autouse=True)
def setup_camera_platform_only():
    """Only setup camera platform."""
    with patch("menuai.components.prusalink.PLATFORMS", [Platform.CAMERA]):
        yield


async def test_camera_no_job(
    menuai: menuai,
    mock_config_entry,
    mock_api,
    menuai_client: ClientSessionGenerator,
) -> None:
    """Test camera while no job active."""
    assert await async_setup_component(menuai, "prusalink", {})
    state = menuai.states.get("camera.mock_title_preview")
    assert state is not None
    assert state.state == "unavailable"

    client = await menuai_client()
    resp = await client.get("/api/camera_proxy/camera.mock_title_preview")
    assert resp.status == 500


async def test_camera_idle_job_mk3(
    menuai: menuai,
    mock_config_entry,
    mock_api,
    mock_job_api_idle_mk3,
    menuai_client: ClientSessionGenerator,
) -> None:
    """Test camera while job state is idle (MK3)."""
    assert await async_setup_component(menuai, "prusalink", {})
    state = menuai.states.get("camera.mock_title_preview")
    assert state is not None
    assert state.state == "unavailable"

    client = await menuai_client()
    resp = await client.get("/api/camera_proxy/camera.mock_title_preview")
    assert resp.status == 500


async def test_camera_active_job(
    menuai: menuai,
    mock_config_entry,
    mock_api,
    mock_job_api_printing,
    menuai_client: ClientSessionGenerator,
) -> None:
    """Test camera while job active."""
    assert await async_setup_component(menuai, "prusalink", {})
    state = menuai.states.get("camera.mock_title_preview")
    assert state is not None
    assert state.state == "idle"

    client = await menuai_client()

    with patch("pyprusalink.PrusaLink.get_file", return_value=b"hello"):
        resp = await client.get("/api/camera_proxy/camera.mock_title_preview")
        assert resp.status == 200
        assert await resp.read() == b"hello"

    # Make sure we hit cached value.
    with patch("pyprusalink.PrusaLink.get_file", side_effect=ValueError):
        resp = await client.get("/api/camera_proxy/camera.mock_title_preview")
        assert resp.status == 200
        assert await resp.read() == b"hello"
