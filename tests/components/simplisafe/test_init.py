"""Define tests for SimpliSafe setup."""

from unittest.mock import patch

from menuai.components.simplisafe import DOMAIN
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component


async def test_base_station_migration(
    menuai: menuai, device_registry: dr.DeviceRegistry, api, config, config_entry
) -> None:
    """Test that errors are shown when duplicates are added."""
    old_identifers = (DOMAIN, 12345)
    new_identifiers = (DOMAIN, "12345")

    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={old_identifers},
        manufacturer="SimpliSafe",
        name="old",
    )

    with (
        patch(
            "menuai.components.simplisafe.config_flow.API.async_from_auth",
            return_value=api,
        ),
        patch(
            "menuai.components.simplisafe.API.async_from_auth",
            return_value=api,
        ),
        patch(
            "menuai.components.simplisafe.API.async_from_refresh_token",
            return_value=api,
        ),
        patch(
            "menuai.components.simplisafe.SimpliSafe._async_start_websocket_loop"
        ),
        patch(
            "menuai.components.simplisafe.PLATFORMS",
            [],
        ),
    ):
        assert await async_setup_component(menuai, DOMAIN, config)
        await menuai.async_block_till_done()

    assert device_registry.async_get_device(identifiers={old_identifers}) is None
    assert device_registry.async_get_device(identifiers={new_identifiers}) is not None
