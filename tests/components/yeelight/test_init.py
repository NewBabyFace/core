"""Test Yeelight."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from yeelight import BulbException, BulbType
from yeelight.aio import KEY_CONNECTED

from menuai.components.yeelight.const import (
    CONF_DETECTED_MODEL,
    CONF_NIGHTLIGHT_SWITCH,
    CONF_NIGHTLIGHT_SWITCH_TYPE,
    DOMAIN,
    NIGHTLIGHT_SWITCH_TYPE_LIGHT,
    STATE_CHANGE_TIME,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import (
    CONF_DEVICES,
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from . import (
    CONFIG_ENTRY_DATA,
    ENTITY_AMBILIGHT,
    ENTITY_BINARY_SENSOR,
    ENTITY_BINARY_SENSOR_TEMPLATE,
    ENTITY_LIGHT,
    ENTITY_NIGHTLIGHT,
    FAIL_TO_BIND_IP,
    ID,
    IP_ADDRESS,
    MODEL,
    MODULE,
    SHORT_ID,
    _mocked_bulb,
    _patch_discovery,
    _patch_discovery_interval,
    _patch_discovery_timeout,
)

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_ip_changes_fallback_discovery(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test Yeelight ip changes and we fallback to discovery."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_ID: ID, CONF_HOST: "5.5.5.5"}, unique_id=ID
    )
    config_entry.add_to_menuai(menuai)

    mocked_fail_bulb = _mocked_bulb(cannot_connect=True)
    mocked_fail_bulb.bulb_type = BulbType.WhiteTempMood
    with (
        patch(f"{MODULE}.AsyncBulb", return_value=mocked_fail_bulb),
        _patch_discovery(),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        assert config_entry.state is ConfigEntryState.SETUP_RETRY
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=2))
        await menuai.async_block_till_done(wait_background_tasks=True)

    # The discovery should update the ip address
    assert config_entry.data[CONF_HOST] == IP_ADDRESS
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    mocked_bulb = _mocked_bulb()

    with patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb), _patch_discovery():
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=10))
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert config_entry.state is ConfigEntryState.LOADED

    binary_sensor_entity_id = ENTITY_BINARY_SENSOR_TEMPLATE.format(
        f"yeelight_color_{SHORT_ID}"
    )
    assert entity_registry.async_get(binary_sensor_entity_id) is not None

    # Make sure we can still reload with the new ip right after we change it
    with patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb), _patch_discovery():
        await menuai.config_entries.async_reload(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert entity_registry.async_get(binary_sensor_entity_id) is not None


async def test_ip_changes_id_missing_cannot_fallback(menuai: menuai) -> None:
    """Test Yeelight ip changes and we fallback to discovery."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: "5.5.5.5"})
    config_entry.add_to_menuai(menuai)

    mocked_bulb = _mocked_bulb(True)
    mocked_bulb.bulb_type = BulbType.WhiteTempMood
    mocked_bulb.async_listen = AsyncMock(side_effect=[BulbException, None, None, None])

    with patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb):
        assert not await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_discovery(menuai: menuai) -> None:
    """Test setting up Yeelight by discovery."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: IP_ADDRESS, **CONFIG_ENTRY_DATA}
    )
    config_entry.add_to_menuai(menuai)

    mocked_bulb = _mocked_bulb()
    with _patch_discovery(), patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert menuai.states.get(ENTITY_BINARY_SENSOR) is not None
    assert menuai.states.get(ENTITY_LIGHT) is not None

    # Unload
    assert await menuai.config_entries.async_unload(config_entry.entry_id)
    assert menuai.states.get(ENTITY_BINARY_SENSOR).state == STATE_UNAVAILABLE
    assert menuai.states.get(ENTITY_LIGHT).state == STATE_UNAVAILABLE

    # Remove
    assert await menuai.config_entries.async_remove(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert menuai.states.get(ENTITY_BINARY_SENSOR) is None
    assert menuai.states.get(ENTITY_LIGHT) is None


_ADAPTERS_WITH_MANUAL_CONFIG = [
    {
        "auto": True,
        "index": 2,
        "default": False,
        "enabled": True,
        "ipv4": [{"address": "192.168.1.5", "network_prefix": 23}],
        "ipv6": [],
        "name": "eth1",
    },
]


async def test_setup_discovery_with_manually_configured_network_adapter(
    menuai: menuai,
) -> None:
    """Test setting up Yeelight by discovery with a manually configured network adapter."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: IP_ADDRESS, **CONFIG_ENTRY_DATA}
    )
    config_entry.add_to_menuai(menuai)

    mocked_bulb = _mocked_bulb()
    with (
        _patch_discovery(),
        patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb),
        patch(
            "menuai.components.zeroconf.network.async_get_adapters",
            return_value=_ADAPTERS_WITH_MANUAL_CONFIG,
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert menuai.states.get(ENTITY_BINARY_SENSOR) is not None
    assert menuai.states.get(ENTITY_LIGHT) is not None

    # Unload
    assert await menuai.config_entries.async_unload(config_entry.entry_id)
    assert menuai.states.get(ENTITY_BINARY_SENSOR).state == STATE_UNAVAILABLE
    assert menuai.states.get(ENTITY_LIGHT).state == STATE_UNAVAILABLE

    # Remove
    assert await menuai.config_entries.async_remove(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert menuai.states.get(ENTITY_BINARY_SENSOR) is None
    assert menuai.states.get(ENTITY_LIGHT) is None


_ADAPTERS_WITH_MANUAL_CONFIG_ONE_FAILING = [
    {
        "auto": True,
        "index": 1,
        "default": False,
        "enabled": True,
        "ipv4": [{"address": FAIL_TO_BIND_IP, "network_prefix": 23}],
        "ipv6": [],
        "name": "eth0",
    },
    {
        "auto": True,
        "index": 2,
        "default": False,
        "enabled": True,
        "ipv4": [{"address": "192.168.1.5", "network_prefix": 23}],
        "ipv6": [],
        "name": "eth1",
    },
]


async def test_setup_discovery_with_manually_configured_network_adapter_one_fails(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test setting up Yeelight by discovery with a manually configured network adapter with one that fails to bind."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: IP_ADDRESS, **CONFIG_ENTRY_DATA}
    )
    config_entry.add_to_menuai(menuai)

    mocked_bulb = _mocked_bulb()
    with (
        _patch_discovery(),
        patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb),
        patch(
            "menuai.components.zeroconf.network.async_get_adapters",
            return_value=_ADAPTERS_WITH_MANUAL_CONFIG_ONE_FAILING,
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert menuai.states.get(ENTITY_BINARY_SENSOR) is not None
    assert menuai.states.get(ENTITY_LIGHT) is not None

    # Unload
    assert await menuai.config_entries.async_unload(config_entry.entry_id)
    assert menuai.states.get(ENTITY_BINARY_SENSOR).state == STATE_UNAVAILABLE
    assert menuai.states.get(ENTITY_LIGHT).state == STATE_UNAVAILABLE

    # Remove
    assert await menuai.config_entries.async_remove(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert menuai.states.get(ENTITY_BINARY_SENSOR) is None
    assert menuai.states.get(ENTITY_LIGHT) is None

    assert f"Failed to setup listener for ('{FAIL_TO_BIND_IP}', 0)" in caplog.text


async def test_setup_import(menuai: menuai) -> None:
    """Test import from yaml."""
    mocked_bulb = _mocked_bulb()
    name = "yeelight"
    with patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb), _patch_discovery():
        assert await async_setup_component(
            menuai,
            DOMAIN,
            {
                DOMAIN: {
                    CONF_DEVICES: {
                        IP_ADDRESS: {
                            CONF_NAME: name,
                            CONF_NIGHTLIGHT_SWITCH_TYPE: NIGHTLIGHT_SWITCH_TYPE_LIGHT,
                        }
                    }
                }
            },
        )
        await menuai.async_block_till_done()

    assert menuai.states.get(f"binary_sensor.{name}_nightlight") is not None
    assert menuai.states.get(f"light.{name}") is not None
    assert menuai.states.get(f"light.{name}_nightlight") is not None
    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert entry.unique_id == "0x000000000015243f"
    assert entry.data[CONF_ID] == "0x000000000015243f"


async def test_unique_ids_device(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test Yeelight unique IDs from yeelight device IDs."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: IP_ADDRESS, **CONFIG_ENTRY_DATA, CONF_NIGHTLIGHT_SWITCH: True},
        unique_id=ID,
    )
    config_entry.add_to_menuai(menuai)

    mocked_bulb = _mocked_bulb()
    mocked_bulb.bulb_type = BulbType.WhiteTempMood
    with _patch_discovery(), patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert (
        entity_registry.async_get(ENTITY_BINARY_SENSOR).unique_id
        == f"{ID}-nightlight_sensor"
    )
    assert entity_registry.async_get(ENTITY_LIGHT).unique_id == ID
    assert entity_registry.async_get(ENTITY_NIGHTLIGHT).unique_id == f"{ID}-nightlight"
    assert entity_registry.async_get(ENTITY_AMBILIGHT).unique_id == f"{ID}-ambilight"


async def test_unique_ids_entry(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test Yeelight unique IDs from entry IDs."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: IP_ADDRESS, CONF_NIGHTLIGHT_SWITCH: True},
    )
    config_entry.add_to_menuai(menuai)

    mocked_bulb = _mocked_bulb()
    mocked_bulb.bulb_type = BulbType.WhiteTempMood

    with _patch_discovery(), patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert (
        entity_registry.async_get(ENTITY_BINARY_SENSOR).unique_id
        == f"{config_entry.entry_id}-nightlight_sensor"
    )
    assert entity_registry.async_get(ENTITY_LIGHT).unique_id == config_entry.entry_id
    assert (
        entity_registry.async_get(ENTITY_NIGHTLIGHT).unique_id
        == f"{config_entry.entry_id}-nightlight"
    )
    assert (
        entity_registry.async_get(ENTITY_AMBILIGHT).unique_id
        == f"{config_entry.entry_id}-ambilight"
    )


async def test_bulb_off_while_adding_in_ha(menuai: menuai) -> None:
    """Test Yeelight off while adding to ha, for example on HA start."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data={**CONFIG_ENTRY_DATA, CONF_HOST: IP_ADDRESS}, unique_id=ID
    )
    config_entry.add_to_menuai(menuai)

    mocked_bulb = _mocked_bulb(cannot_connect=True)
    mocked_bulb.bulb_type = BulbType.WhiteTempMood

    with (
        patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb),
        _patch_discovery(no_device=True),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY

    with (
        patch(f"{MODULE}.AsyncBulb", return_value=_mocked_bulb()),
        _patch_discovery(no_device=True),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
    ):
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=2))
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert config_entry.state is ConfigEntryState.LOADED


async def test_async_listen_error_late_discovery(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the async listen error."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=CONFIG_ENTRY_DATA)
    config_entry.add_to_menuai(menuai)

    mocked_bulb = _mocked_bulb(cannot_connect=True)

    with _patch_discovery(), patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=5))
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    await menuai.async_block_till_done()
    assert "Waiting for 0x15243f to be discovered" in caplog.text

    with _patch_discovery(), patch(f"{MODULE}.AsyncBulb", return_value=_mocked_bulb()):
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=10))
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.data[CONF_DETECTED_MODEL] == MODEL


async def test_fail_to_fetch_initial_state(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test failing to fetch initial state results in a retry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: IP_ADDRESS, **CONFIG_ENTRY_DATA}
    )
    config_entry.add_to_menuai(menuai)

    mocked_bulb = _mocked_bulb()
    del mocked_bulb.last_properties["power"]
    del mocked_bulb.last_properties["main_power"]

    with _patch_discovery(), patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=5))
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    await menuai.async_block_till_done()
    assert "Could not fetch initial state; try power cycling the device" in caplog.text

    with _patch_discovery(), patch(f"{MODULE}.AsyncBulb", return_value=_mocked_bulb()):
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=10))
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert config_entry.state is ConfigEntryState.LOADED


async def test_unload_before_discovery(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test unloading before discovery."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=CONFIG_ENTRY_DATA)
    config_entry.add_to_menuai(menuai)

    mocked_bulb = _mocked_bulb(cannot_connect=True)

    with (
        _patch_discovery(no_device=True),
        patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_async_listen_error_has_host_with_id(menuai: menuai) -> None:
    """Test the async listen error."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_ID: ID, CONF_HOST: "127.0.0.1"}
    )
    config_entry.add_to_menuai(menuai)

    with (
        _patch_discovery(no_device=True),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
        patch(f"{MODULE}.AsyncBulb", return_value=_mocked_bulb(cannot_connect=True)),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_async_listen_error_has_host_without_id(menuai: menuai) -> None:
    """Test the async listen error but no id."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: "127.0.0.1"})
    config_entry.add_to_menuai(menuai)

    with (
        _patch_discovery(no_device=True),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
        patch(f"{MODULE}.AsyncBulb", return_value=_mocked_bulb(cannot_connect=True)),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_async_setup_with_missing_id(menuai: menuai) -> None:
    """Test that setting adds the missing CONF_ID from unique_id."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ID,
        data={CONF_HOST: "127.0.0.1"},
        options={CONF_NAME: "Test name"},
    )
    config_entry.add_to_menuai(menuai)

    with (
        _patch_discovery(),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
        patch(f"{MODULE}.AsyncBulb", return_value=_mocked_bulb(cannot_connect=True)),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.SETUP_RETRY
        assert config_entry.data[CONF_ID] == ID
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=2))
        await menuai.async_block_till_done(wait_background_tasks=True)

    with (
        _patch_discovery(),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
        patch(f"{MODULE}.AsyncBulb", return_value=_mocked_bulb()),
    ):
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=4))
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert config_entry.state is ConfigEntryState.LOADED


async def test_async_setup_with_missing_unique_id(menuai: menuai) -> None:
    """Test that setting adds the missing unique_id from CONF_ID."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "127.0.0.1", CONF_ID: ID},
        options={CONF_NAME: "Test name"},
    )
    config_entry.add_to_menuai(menuai)

    with (
        _patch_discovery(),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
        patch(f"{MODULE}.AsyncBulb", return_value=_mocked_bulb(cannot_connect=True)),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.SETUP_RETRY
        assert config_entry.unique_id == ID
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=2))
        await menuai.async_block_till_done(wait_background_tasks=True)

    with (
        _patch_discovery(),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
        patch(f"{MODULE}.AsyncBulb", return_value=_mocked_bulb()),
    ):
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=4))
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert config_entry.state is ConfigEntryState.LOADED


async def test_connection_dropped_resyncs_properties(menuai: menuai) -> None:
    """Test handling a connection drop results in a property resync."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ID,
        data={CONF_HOST: "127.0.0.1"},
        options={CONF_NAME: "Test name"},
    )
    config_entry.add_to_menuai(menuai)
    mocked_bulb = _mocked_bulb()

    with (
        _patch_discovery(),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
        patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert len(mocked_bulb.async_get_properties.mock_calls) == 1
        mocked_bulb._async_callback({KEY_CONNECTED: False})
        await menuai.async_block_till_done()
        assert menuai.states.get("light.test_name").state == STATE_UNAVAILABLE
        assert len(mocked_bulb.async_get_properties.mock_calls) == 1
        mocked_bulb._async_callback({KEY_CONNECTED: True})
        async_fire_time_changed(
            menuai, dt_util.utcnow() + timedelta(seconds=STATE_CHANGE_TIME)
        )
        await menuai.async_block_till_done()
        assert menuai.states.get("light.test_name").state == STATE_ON
        assert len(mocked_bulb.async_get_properties.mock_calls) == 2


async def test_oserror_on_first_update_results_in_unavailable(
    menuai: menuai,
) -> None:
    """Test that an OSError on first update results in unavailable."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ID,
        data={CONF_HOST: "127.0.0.1"},
        options={CONF_NAME: "Test name"},
    )
    config_entry.add_to_menuai(menuai)
    mocked_bulb = _mocked_bulb()
    mocked_bulb.async_get_properties = AsyncMock(side_effect=OSError)

    with (
        _patch_discovery(),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
        patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert menuai.states.get("light.test_name").state == STATE_UNAVAILABLE


@pytest.mark.parametrize("exception", [BulbException, TimeoutError])
async def test_non_oserror_exception_on_first_update(
    menuai: menuai, exception: Exception
) -> None:
    """Test that an exceptions other than OSError on first update do not result in unavailable.

    The unavailable state will come as a push update in this case
    """
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ID,
        data={CONF_HOST: "127.0.0.1"},
        options={CONF_NAME: "Test name"},
    )
    config_entry.add_to_menuai(menuai)
    mocked_bulb = _mocked_bulb()
    mocked_bulb.async_get_properties = AsyncMock(side_effect=exception)

    with (
        _patch_discovery(),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
        patch(f"{MODULE}.AsyncBulb", return_value=mocked_bulb),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert menuai.states.get("light.test_name").state != STATE_UNAVAILABLE


async def test_async_setup_with_discovery_not_working(menuai: menuai) -> None:
    """Test we can setup even if discovery is broken."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "127.0.0.1", CONF_ID: ID},
        options={},
        unique_id=ID,
    )
    config_entry.add_to_menuai(menuai)

    with (
        _patch_discovery(no_device=True),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
        patch(f"{MODULE}.AsyncBulb", return_value=_mocked_bulb()),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.LOADED

    assert menuai.states.get("light.yeelight_color_0x15243f").state == STATE_ON


async def test_async_setup_retries_with_wrong_device(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the config entry enters a retry state with the wrong device."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: IP_ADDRESS, CONF_ID: "0x0000000000999999"},
        options={},
        unique_id="0x0000000000999999",
    )
    config_entry.add_to_menuai(menuai)

    with (
        _patch_discovery(),
        _patch_discovery_timeout(),
        _patch_discovery_interval(),
        patch(f"{MODULE}.AsyncBulb", return_value=_mocked_bulb()),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert (
        "Unexpected device found at 192.168.1.239; expected 0x0000000000999999, "
        "found 0x000000000015243f; Retrying in"
    ) in caplog.text
