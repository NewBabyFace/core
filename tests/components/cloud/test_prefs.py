"""Test Cloud preferences."""

from typing import Any
from unittest.mock import ANY, MagicMock, patch

import pytest

from menuai.auth.const import GROUP_ID_ADMIN
from menuai.components.cloud.const import DOMAIN, PREF_TTS_DEFAULT_VOICE
from menuai.components.cloud.prefs import STORAGE_KEY, CloudPreferences
from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_set_username(menuai: menuai) -> None:
    """Test we clear config if we set different username."""
    prefs = CloudPreferences(menuai)
    await prefs.async_initialize()

    assert prefs.google_enabled

    await prefs.async_update(google_enabled=False)

    assert not prefs.google_enabled

    await prefs.async_set_username("new-username")

    assert prefs.google_enabled


async def test_erase_config(menuai: menuai) -> None:
    """Test erasing config."""
    prefs = CloudPreferences(menuai)
    await prefs.async_initialize()
    assert prefs._prefs == {
        **prefs._empty_config(""),
        "google_local_webhook_id": ANY,
        "instance_id": ANY,
    }

    await prefs.async_update(google_enabled=False)
    assert prefs._prefs == {
        **prefs._empty_config(""),
        "google_enabled": False,
        "google_local_webhook_id": ANY,
        "instance_id": ANY,
    }

    await prefs.async_erase_config()
    assert prefs._prefs == {
        **prefs._empty_config(""),
        "google_local_webhook_id": ANY,
        "instance_id": ANY,
    }


async def test_set_username_migration(menuai: menuai) -> None:
    """Test we do not clear config if we had no username."""
    prefs = CloudPreferences(menuai)

    with patch.object(prefs, "_empty_config", return_value=prefs._empty_config(None)):
        await prefs.async_initialize()

    assert prefs.google_enabled

    await prefs.async_update(google_enabled=False)

    assert not prefs.google_enabled

    await prefs.async_set_username("new-username")

    assert not prefs.google_enabled


async def test_set_new_username(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test if setting new username returns true."""
    menuai_storage[STORAGE_KEY] = {"version": 1, "data": {"username": "old-user"}}

    prefs = CloudPreferences(menuai)
    await prefs.async_initialize()

    assert not await prefs.async_set_username("old-user")

    assert await prefs.async_set_username("new-user")


async def test_load_invalid_cloud_user(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test loading cloud user with invalid storage."""
    menuai_storage[STORAGE_KEY] = {"version": 1, "data": {"cloud_user": "non-existing"}}

    prefs = CloudPreferences(menuai)
    await prefs.async_initialize()

    cloud_user_id = await prefs.get_cloud_user()

    assert cloud_user_id != "non-existing"

    cloud_user = await menuai.auth.async_get_user(
        menuai_storage[STORAGE_KEY]["data"]["cloud_user"]
    )

    assert cloud_user
    assert cloud_user.groups[0].id == GROUP_ID_ADMIN


async def test_setup_remove_cloud_user(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test creating and removing cloud user."""
    menuai_storage[STORAGE_KEY] = {"version": 1, "data": {"cloud_user": None}}

    prefs = CloudPreferences(menuai)
    await prefs.async_initialize()
    await prefs.async_set_username("user1")

    cloud_user = await menuai.auth.async_get_user(await prefs.get_cloud_user())

    assert cloud_user
    assert cloud_user.groups[0].id == GROUP_ID_ADMIN

    await prefs.async_set_username("user2")

    cloud_user2 = await menuai.auth.async_get_user(await prefs.get_cloud_user())

    assert cloud_user2
    assert cloud_user2.groups[0].id == GROUP_ID_ADMIN
    assert cloud_user2.id != cloud_user.id


@pytest.mark.parametrize(
    ("google_assistant_users", "google_connected"),
    [([], False), (["cloud-user"], True), (["other-user"], False)],
)
async def test_import_google_assistant_settings(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    google_assistant_users: list[str],
    google_connected: bool,
) -> None:
    """Test importing from the google assistant store."""
    menuai_storage[STORAGE_KEY] = {"version": 1, "data": {"username": "cloud-user"}}

    with patch(
        "menuai.components.cloud.prefs.async_get_google_assistant_users"
    ) as mock_get_users:
        mock_get_users.return_value = google_assistant_users
        prefs = CloudPreferences(menuai)
        await prefs.async_initialize()
        assert prefs.google_connected == google_connected


@pytest.mark.parametrize(
    ("stored_language", "expected_language", "voice"),
    [("en-US", "en-US", "GuyNeural"), ("missing_language", "en-US", "JennyNeural")],
)
async def test_tts_default_voice_legacy_gender(
    menuai: menuai,
    cloud: MagicMock,
    menuai_storage: dict[str, Any],
    stored_language: str,
    expected_language: str,
    voice: str,
) -> None:
    """Test tts with legacy gender as default tts voice setting in storage."""
    menuai_storage[STORAGE_KEY] = {
        "version": 1,
        "data": {PREF_TTS_DEFAULT_VOICE: [stored_language, "male"]},
    }
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()

    assert cloud.client.prefs.tts_default_voice == (expected_language, voice)
