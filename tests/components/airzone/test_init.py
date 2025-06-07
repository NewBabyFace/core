"""Define tests for the Airzone init."""

from unittest.mock import patch

from aioairzone.const import DEFAULT_SYSTEM_ID
from aioairzone.exceptions import HotWaterNotAvailable, InvalidMethod, SystemOutOfRange

from menuai.components.airzone.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_ID
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .util import CONFIG, HVAC_MOCK, HVAC_VERSION_MOCK, HVAC_WEBSERVER_MOCK, USER_INPUT

from tests.common import MockConfigEntry


async def test_unique_id_migrate(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test unique id migration."""

    config_entry = MockConfigEntry(
        minor_version=2,
        domain=DOMAIN,
        data=CONFIG,
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_dhw",
            side_effect=HotWaterNotAvailable,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_hvac",
            return_value=HVAC_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_hvac_systems",
            side_effect=SystemOutOfRange,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_version",
            return_value=HVAC_VERSION_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_webserver",
            side_effect=InvalidMethod,
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert not config_entry.unique_id
    assert (
        entity_registry.async_get("sensor.salon_temperature").unique_id
        == f"{config_entry.entry_id}_1:1_temp"
    )

    with (
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_dhw",
            side_effect=HotWaterNotAvailable,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_hvac",
            return_value=HVAC_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_hvac_systems",
            side_effect=SystemOutOfRange,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_version",
            return_value=HVAC_VERSION_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_webserver",
            return_value=HVAC_WEBSERVER_MOCK,
        ),
    ):
        await menuai.config_entries.async_reload(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.unique_id
    assert (
        entity_registry.async_get("sensor.salon_temperature").unique_id
        == f"{config_entry.unique_id}_1:1_temp"
    )


async def test_unload_entry(menuai: menuai) -> None:
    """Test unload."""

    config_entry = MockConfigEntry(
        minor_version=2,
        data=CONFIG,
        domain=DOMAIN,
        unique_id="airzone_unique_id",
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.airzone.AirzoneLocalApi.validate",
            return_value=None,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.update",
            return_value=None,
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.LOADED

        await menuai.config_entries.async_unload(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_migrate_entry_v2(menuai: menuai) -> None:
    """Test entry migration to v2."""

    config_entry = MockConfigEntry(
        minor_version=1,
        data=USER_INPUT,
        domain=DOMAIN,
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_dhw",
            side_effect=HotWaterNotAvailable,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_hvac",
            return_value=HVAC_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_hvac_systems",
            side_effect=SystemOutOfRange,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_version",
            return_value=HVAC_VERSION_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_webserver",
            side_effect=InvalidMethod,
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.minor_version == 2
    assert config_entry.data.get(CONF_ID) == DEFAULT_SYSTEM_ID
