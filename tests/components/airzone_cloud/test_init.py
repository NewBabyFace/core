"""Define tests for the Airzone Cloud init."""

from unittest.mock import patch

from aioairzone_cloud.exceptions import AirzoneTimeout

from menuai.components.airzone_cloud.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from .util import CONFIG

from tests.common import MockConfigEntry


async def test_unload_entry(menuai: menuai) -> None:
    """Test unload."""

    config_entry = MockConfigEntry(
        data=CONFIG,
        domain=DOMAIN,
        unique_id="airzone_cloud_unique_id",
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.login",
            return_value=None,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.logout",
            return_value=None,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.list_installations",
            return_value=[],
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.update_installation",
            return_value=None,
        ),
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.update",
            return_value=None,
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.LOADED

        await menuai.config_entries.async_unload(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_init_api_timeout(menuai: menuai) -> None:
    """Test API timeouts when loading the Airzone Cloud integration."""

    with patch(
        "menuai.components.airzone_cloud.AirzoneCloudApi.login",
        side_effect=AirzoneTimeout,
    ):
        config_entry = MockConfigEntry(
            data=CONFIG,
            domain=DOMAIN,
            unique_id="airzone_cloud_unique_id",
        )
        config_entry.add_to_menuai(menuai)

        assert await menuai.config_entries.async_setup(config_entry.entry_id) is False
