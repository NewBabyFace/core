"""Test MenuAI Cast."""

from unittest.mock import patch

import pytest

from menuai.components.cast import DOMAIN, home_assistant_cast
from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config
from menuai.exceptions import menuaiError

from tests.common import MockConfigEntry, async_mock_signal


@pytest.mark.usefixtures("mock_zeroconf")
async def test_service_show_view(menuai: menuai) -> None:
    """Test showing a view."""
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_menuai(menuai)
    await home_assistant_cast.async_setup_ha_cast(menuai, entry)
    calls = async_mock_signal(menuai, home_assistant_cast.SIGNAL_menuai_CAST_SHOW_VIEW)

    # No valid URL
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            "cast",
            "show_lovelace_view",
            {"entity_id": "media_player.kitchen", "view_path": "mock_path"},
            blocking=True,
        )

    # Set valid URL
    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://example.com"},
    )
    await menuai.services.async_call(
        "cast",
        "show_lovelace_view",
        {"entity_id": "media_player.kitchen", "view_path": "mock_path"},
        blocking=True,
    )

    assert len(calls) == 1
    controller_data, entity_id, view_path, url_path = calls[0]
    assert controller_data["menuai_url"] == "https://example.com"
    assert controller_data["client_id"] is None
    # Verify user did not accidentally submit their dev app id
    assert "supporting_app_id" not in controller_data
    assert entity_id == "media_player.kitchen"
    assert view_path == "mock_path"
    assert url_path is None


@pytest.mark.usefixtures("mock_zeroconf")
async def test_service_show_view_dashboard(menuai: menuai) -> None:
    """Test casting a specific dashboard."""
    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://example.com"},
    )
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_menuai(menuai)
    await home_assistant_cast.async_setup_ha_cast(menuai, entry)
    calls = async_mock_signal(menuai, home_assistant_cast.SIGNAL_menuai_CAST_SHOW_VIEW)

    await menuai.services.async_call(
        "cast",
        "show_lovelace_view",
        {
            "entity_id": "media_player.kitchen",
            "view_path": "mock_path",
            "dashboard_path": "mock-dashboard",
        },
        blocking=True,
    )

    assert len(calls) == 1
    _controller_data, entity_id, view_path, url_path = calls[0]
    assert entity_id == "media_player.kitchen"
    assert view_path == "mock_path"
    assert url_path == "mock-dashboard"


@pytest.mark.usefixtures("mock_zeroconf")
async def test_use_cloud_url(menuai: menuai) -> None:
    """Test that we fall back to cloud url."""
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://example.local:8123"},
    )
    menuai.config.components.add("cloud")

    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_menuai(menuai)
    await home_assistant_cast.async_setup_ha_cast(menuai, entry)
    calls = async_mock_signal(menuai, home_assistant_cast.SIGNAL_menuai_CAST_SHOW_VIEW)

    with patch(
        "menuai.components.cloud.async_remote_ui_url",
        return_value="https://something.nabu.casa",
    ):
        await menuai.services.async_call(
            "cast",
            "show_lovelace_view",
            {"entity_id": "media_player.kitchen", "view_path": "mock_path"},
            blocking=True,
        )

    assert len(calls) == 1
    controller_data = calls[0][0]
    assert controller_data["menuai_url"] == "https://something.nabu.casa"


@pytest.mark.usefixtures("mock_zeroconf")
async def test_remove_entry(menuai: menuai) -> None:
    """Test removing config entry removes user."""
    entry = MockConfigEntry(
        data={},
        domain="cast",
        title="Google Cast",
    )

    entry.add_to_menuai(menuai)

    with (
        patch("pychromecast.discovery.discover_chromecasts", return_value=(True, None)),
        patch("pychromecast.discovery.stop_discovery"),
    ):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
    assert "cast" in menuai.config.components

    user_id = entry.data.get("user_id")
    assert await menuai.auth.async_get_user(user_id)

    assert await menuai.config_entries.async_remove(entry.entry_id)
    assert not await menuai.auth.async_get_user(user_id)
