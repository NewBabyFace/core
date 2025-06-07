"""Test init of IMGW-PIB integration."""

from unittest.mock import AsyncMock, patch

from imgw_pib import ApiError

from menuai.components.binary_sensor import DOMAIN as BINARY_SENSOR_PLATFORM
from menuai.components.imgw_pib.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import MockConfigEntry


async def test_config_not_ready(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test for setup failure if the connection to the service fails."""
    with patch(
        "menuai.components.imgw_pib.ImgwPib.create",
        side_effect=ApiError("API Error"),
    ):
        await init_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(
    menuai: menuai,
    mock_imgw_pib_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test successful unload of entry."""
    await init_integration(menuai, mock_config_entry)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_remove_binary_sensor_entity(
    menuai: menuai,
    mock_imgw_pib_client: AsyncMock,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test removing a binary_sensor entity."""
    entity_id = "binary_sensor.river_name_station_name_flood_alarm"
    mock_config_entry.add_to_menuai(menuai)

    entity_registry.async_get_or_create(
        BINARY_SENSOR_PLATFORM,
        DOMAIN,
        "123_flood_alarm",
        suggested_object_id=entity_id.rsplit(".", maxsplit=1)[-1],
        config_entry=mock_config_entry,
    )

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_id) is None
