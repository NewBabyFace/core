"""Define tests for the Daikin init."""

from datetime import timedelta
from unittest.mock import AsyncMock, PropertyMock, patch

from aiohttp import ClientConnectionError
from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.daikin import update_unique_id
from menuai.components.daikin.const import DOMAIN, KEY_MAC
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_HOST, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from .test_config_flow import HOST, MAC

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.fixture
def mock_daikin():
    """Mock pydaikin."""

    async def mock_daikin_factory(*args, **kwargs):
        """Mock the init function in pydaikin."""
        return Appliance

    with patch("menuai.components.daikin.DaikinFactory") as Appliance:
        Appliance.side_effect = mock_daikin_factory
        type(Appliance).update_status = AsyncMock()
        type(Appliance).device_ip = PropertyMock(return_value=HOST)
        type(Appliance).inside_temperature = PropertyMock(return_value=22)
        type(Appliance).target_temperature = PropertyMock(return_value=22)
        type(Appliance).zones = PropertyMock(return_value=[("Zone 1", "0", 0)])
        type(Appliance).fan_rate = PropertyMock(return_value=[])
        type(Appliance).swing_modes = PropertyMock(return_value=[])
        yield Appliance


DATA = {
    "ver": "1_1_8",
    "name": "DaikinAP00000",
    "mac": MAC,
    "model": "NOTSUPPORT",
}


INVALID_DATA = {**DATA, "name": None, "mac": HOST}


async def test_duplicate_removal(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_daikin,
) -> None:
    """Test duplicate device removal."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=HOST,
        title=None,
        data={CONF_HOST: HOST, KEY_MAC: HOST},
    )
    config_entry.add_to_menuai(menuai)

    type(mock_daikin).mac = PropertyMock(return_value=HOST)
    type(mock_daikin).values = PropertyMock(return_value=INVALID_DATA)

    with patch(
        "menuai.components.daikin.async_migrate_unique_id", return_value=None
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)

        await menuai.async_block_till_done()

        assert config_entry.unique_id != MAC

        type(mock_daikin).mac = PropertyMock(return_value=MAC)
        type(mock_daikin).values = PropertyMock(return_value=DATA)

        assert await menuai.config_entries.async_reload(config_entry.entry_id)
        await menuai.async_block_till_done()

        assert (
            device_registry.async_get_device({}, {(KEY_MAC, MAC)}).name
            == "DaikinAP00000"
        )

        assert device_registry.async_get_device({}, {(KEY_MAC, HOST)}).name is None

        assert entity_registry.async_get("climate.daikin_127_0_0_1").unique_id == HOST
        assert entity_registry.async_get("switch.none_zone_1").unique_id.startswith(
            HOST
        )

        assert entity_registry.async_get("climate.daikinap00000").unique_id == MAC
        assert entity_registry.async_get(
            "switch.daikinap00000_zone_1"
        ).unique_id.startswith(MAC)

    assert await menuai.config_entries.async_reload(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert (
        device_registry.async_get_device({}, {(KEY_MAC, MAC)}).name == "DaikinAP00000"
    )

    assert entity_registry.async_get("climate.daikinap00000") is None
    assert entity_registry.async_get("switch.daikinap00000_zone_1") is None

    assert entity_registry.async_get("climate.daikin_127_0_0_1").unique_id == MAC
    assert entity_registry.async_get("switch.none_zone_1").unique_id.startswith(MAC)


async def test_unique_id_migrate(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_daikin,
) -> None:
    """Test unique id migration."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=HOST,
        title=None,
        data={CONF_HOST: HOST, KEY_MAC: HOST},
    )
    config_entry.add_to_menuai(menuai)

    type(mock_daikin).mac = PropertyMock(return_value=HOST)
    type(mock_daikin).values = PropertyMock(return_value=INVALID_DATA)

    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.unique_id == HOST

    assert device_registry.async_get_device(connections={(KEY_MAC, HOST)}).name is None

    entity = entity_registry.async_get("climate.daikin_127_0_0_1")
    assert entity.unique_id == HOST
    assert update_unique_id(entity, MAC) is not None

    assert entity_registry.async_get("switch.none_zone_1").unique_id.startswith(HOST)

    type(mock_daikin).mac = PropertyMock(return_value=MAC)
    type(mock_daikin).values = PropertyMock(return_value=DATA)

    assert config_entry.unique_id != MAC

    assert await menuai.config_entries.async_reload(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.unique_id == MAC

    assert (
        device_registry.async_get_device(connections={(KEY_MAC, MAC)}).name
        == "DaikinAP00000"
    )

    entity = entity_registry.async_get("climate.daikin_127_0_0_1")
    assert entity.unique_id == MAC
    assert update_unique_id(entity, MAC) is None

    assert entity_registry.async_get("switch.none_zone_1").unique_id.startswith(MAC)


async def test_client_update_connection_error(
    menuai: menuai, mock_daikin, freezer: FrozenDateTimeFactory
) -> None:
    """Test client connection error on update."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MAC,
        data={CONF_HOST: HOST, KEY_MAC: MAC},
    )
    config_entry.add_to_menuai(menuai)

    type(mock_daikin).mac = PropertyMock(return_value=MAC)
    type(mock_daikin).values = PropertyMock(return_value=DATA)

    await menuai.config_entries.async_setup(config_entry.entry_id)

    assert menuai.states.get("climate.daikinap00000").state != STATE_UNAVAILABLE

    type(mock_daikin).update_status.side_effect = ClientConnectionError

    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get("climate.daikinap00000").state == STATE_UNAVAILABLE

    assert mock_daikin.update_status.call_count == 2


async def test_client_connection_error(menuai: menuai, mock_daikin) -> None:
    """Test client connection error on setup."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MAC,
        data={CONF_HOST: HOST, KEY_MAC: MAC},
    )
    config_entry.add_to_menuai(menuai)

    mock_daikin.side_effect = ClientConnectionError
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_timeout_error(menuai: menuai, mock_daikin) -> None:
    """Test timeout error on setup."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MAC,
        data={CONF_HOST: HOST, KEY_MAC: MAC},
    )
    config_entry.add_to_menuai(menuai)

    mock_daikin.side_effect = TimeoutError
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
