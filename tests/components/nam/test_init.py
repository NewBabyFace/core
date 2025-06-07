"""Test init of Nettigo Air Monitor integration."""

from unittest.mock import patch

from nettigo_air_monitor import ApiError, AuthFailedError

from menuai.components.air_quality import DOMAIN as AIR_QUALITY_PLATFORM
from menuai.components.nam.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import MockConfigEntry


async def test_async_setup_entry(menuai: menuai) -> None:
    """Test a successful setup entry."""
    await init_integration(menuai)

    state = menuai.states.get("sensor.nettigo_air_monitor_sds011_pm2_5")
    assert state is not None
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "11.03"


async def test_config_not_ready(menuai: menuai) -> None:
    """Test for setup failure if the connection to the device fails."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="10.10.2.3",
        unique_id="aa:bb:cc:dd:ee:ff",
        data={"host": "10.10.2.3"},
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.nam.NettigoAirMonitor.initialize",
        side_effect=ApiError("API Error"),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_config_not_ready_while_checking_credentials(menuai: menuai) -> None:
    """Test for setup failure if the connection fails while checking credentials."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="10.10.2.3",
        unique_id="aa:bb:cc:dd:ee:ff",
        data={"host": "10.10.2.3"},
    )
    entry.add_to_menuai(menuai)

    with (
        patch("menuai.components.nam.NettigoAirMonitor.initialize"),
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
            side_effect=ApiError("API Error"),
        ),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_config_auth_failed(menuai: menuai) -> None:
    """Test for setup failure if the auth fails."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="10.10.2.3",
        unique_id="aa:bb:cc:dd:ee:ff",
        data={"host": "10.10.2.3"},
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.nam.NettigoAirMonitor.async_check_credentials",
        side_effect=AuthFailedError("Authorization has failed"),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_unload_entry(menuai: menuai) -> None:
    """Test successful unload of entry."""
    entry = await init_integration(menuai)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_remove_air_quality_entities(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test remove air_quality entities from registry."""
    entity_registry.async_get_or_create(
        AIR_QUALITY_PLATFORM,
        DOMAIN,
        "aa:bb:cc:dd:ee:ff-sds011",
        suggested_object_id="nettigo_air_monitor_sds011",
        disabled_by=None,
    )

    entity_registry.async_get_or_create(
        AIR_QUALITY_PLATFORM,
        DOMAIN,
        "aa:bb:cc:dd:ee:ff-sps30",
        suggested_object_id="nettigo_air_monitor_sps30",
        disabled_by=None,
    )

    await init_integration(menuai)

    entry = entity_registry.async_get("air_quality.nettigo_air_monitor_sds011")
    assert entry is None

    entry = entity_registry.async_get("air_quality.nettigo_air_monitor_sps30")
    assert entry is None
