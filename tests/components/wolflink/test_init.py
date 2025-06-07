"""Test the Wolf SmartSet Service."""

from unittest.mock import patch

from httpx import RequestError

from menuai.components.wolflink.const import DEVICE_ID, DOMAIN, MANUFACTURER
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .const import CONFIG

from tests.common import MockConfigEntry


async def test_unique_id_migration(
    menuai: menuai, device_registry: dr.DeviceRegistry
) -> None:
    """Test already configured while creating entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, unique_id=CONFIG[DEVICE_ID], data=CONFIG
    )
    config_entry.add_to_menuai(menuai)

    device_id = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, CONFIG[DEVICE_ID])},
        configuration_url="https://www.wolf-smartset.com/",
        manufacturer=MANUFACTURER,
    ).id

    assert config_entry.version == 1
    assert config_entry.minor_version == 1
    assert config_entry.unique_id == 1234
    assert (
        menuai.config_entries.async_entry_for_domain_unique_id(DOMAIN, 1234)
        is config_entry
    )
    assert menuai.config_entries.async_entry_for_domain_unique_id(DOMAIN, "1234") is None
    assert device_registry.async_get(device_id).identifiers == {(DOMAIN, 1234)}

    with (
        patch(
            "menuai.components.wolflink.fetch_parameters",
            side_effect=RequestError("Unable to fetch parameters"),
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)

    assert config_entry.version == 1
    assert config_entry.minor_version == 2
    assert config_entry.unique_id == "1234"
    assert (
        menuai.config_entries.async_entry_for_domain_unique_id(DOMAIN, "1234")
        is config_entry
    )
    assert menuai.config_entries.async_entry_for_domain_unique_id(DOMAIN, 1234) is None

    assert device_registry.async_get(device_id).identifiers == {(DOMAIN, "1234")}
