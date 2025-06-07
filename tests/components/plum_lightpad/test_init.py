"""Tests for the Plum Lightpad config flow."""

from unittest.mock import Mock, patch

from aiohttp import ContentTypeError
from requests.exceptions import HTTPError

from menuai.components.plum_lightpad.const import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


async def test_async_setup_no_domain_config(menuai: menuai) -> None:
    """Test setup without configuration is noop."""
    result = await async_setup_component(menuai, DOMAIN, {})

    assert result is True
    assert DOMAIN not in menuai.data


async def test_async_setup_entry_sets_up_light(menuai: menuai) -> None:
    """Test that configuring entry sets up light domain."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test-plum-username", "password": "test-plum-password"},
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.plum_lightpad.utils.Plum.loadCloudData"
        ) as mock_loadCloudData,
        patch(
            "menuai.components.plum_lightpad.light.async_setup_entry"
        ) as mock_light_async_setup_entry,
    ):
        result = await menuai.config_entries.async_setup(config_entry.entry_id)
        assert result is True

        await menuai.async_block_till_done()

    assert len(mock_loadCloudData.mock_calls) == 1
    assert len(mock_light_async_setup_entry.mock_calls) == 1


async def test_async_setup_entry_handles_auth_error(menuai: menuai) -> None:
    """Test that configuring entry handles Plum Cloud authentication error."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test-plum-username", "password": "test-plum-password"},
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.plum_lightpad.utils.Plum.loadCloudData",
            side_effect=ContentTypeError(Mock(), None),
        ),
        patch(
            "menuai.components.plum_lightpad.light.async_setup_entry"
        ) as mock_light_async_setup_entry,
    ):
        result = await menuai.config_entries.async_setup(config_entry.entry_id)

    assert result is False
    assert len(mock_light_async_setup_entry.mock_calls) == 0


async def test_async_setup_entry_handles_http_error(menuai: menuai) -> None:
    """Test that configuring entry handles HTTP error."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test-plum-username", "password": "test-plum-password"},
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.plum_lightpad.utils.Plum.loadCloudData",
            side_effect=HTTPError,
        ),
        patch(
            "menuai.components.plum_lightpad.light.async_setup_entry"
        ) as mock_light_async_setup_entry,
    ):
        result = await menuai.config_entries.async_setup(config_entry.entry_id)

    assert result is False
    assert len(mock_light_async_setup_entry.mock_calls) == 0
