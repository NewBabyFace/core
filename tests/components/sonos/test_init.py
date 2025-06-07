"""Tests for the Sonos config flow."""

import asyncio
from datetime import timedelta
import logging
from unittest.mock import Mock, patch

import pytest

from menuai import config_entries
from menuai.components import sonos
from menuai.components.sonos import SonosDiscoveryManager
from menuai.components.sonos.const import (
    DATA_SONOS_DISCOVERY_MANAGER,
    SONOS_SPEAKER_ACTIVITY,
)
from menuai.components.sonos.exception import SonosUpdateError
from menuai.core import menuai, callback
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import entity_registry as er
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.service_info.zeroconf import ZeroconfServiceInfo
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from .conftest import MockSoCo, SoCoMockFactory

from tests.common import async_fire_time_changed


async def test_creating_entry_sets_up_media_player(
    menuai: menuai, zeroconf_payload: ZeroconfServiceInfo
) -> None:
    """Test setting up Sonos loads the media player."""

    # Initiate a discovery to allow a user config flow
    await menuai.config_entries.flow.async_init(
        sonos.DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=zeroconf_payload,
    )

    with patch(
        "menuai.components.sonos.media_player.async_setup_entry",
    ) as mock_setup:
        result = await menuai.config_entries.flow.async_init(
            sonos.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Confirmation form
        assert result["type"] is FlowResultType.FORM

        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["type"] is FlowResultType.CREATE_ENTRY

        await menuai.async_block_till_done(wait_background_tasks=True)

    assert len(mock_setup.mock_calls) == 1


async def test_configuring_sonos_creates_entry(menuai: menuai) -> None:
    """Test that specifying config will create an entry."""
    with patch(
        "menuai.components.sonos.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        await async_setup_component(
            menuai,
            sonos.DOMAIN,
            {"sonos": {"media_player": {"interface_addr": "127.0.0.1"}}},
        )
        await menuai.async_block_till_done()

    assert len(mock_setup.mock_calls) == 1


async def test_not_configuring_sonos_not_creates_entry(menuai: menuai) -> None:
    """Test that no config will not create an entry."""
    with patch(
        "menuai.components.sonos.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        await async_setup_component(menuai, sonos.DOMAIN, {})
        await menuai.async_block_till_done()

    assert len(mock_setup.mock_calls) == 0


async def test_async_poll_manual_hosts_warnings(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that host warnings are not logged repeatedly."""
    await async_setup_component(
        menuai,
        sonos.DOMAIN,
        {"sonos": {"media_player": {"interface_addr": "127.0.0.1"}}},
    )
    await menuai.async_block_till_done()
    manager: SonosDiscoveryManager = menuai.data[DATA_SONOS_DISCOVERY_MANAGER]
    manager.hosts.add("10.10.10.10")
    with (
        caplog.at_level(logging.DEBUG),
        patch.object(manager, "_async_handle_discovery_message"),
        patch(
            "menuai.components.sonos.async_call_later"
        ) as mock_async_call_later,
        patch("menuai.components.sonos.async_dispatcher_send"),
        patch(
            "menuai.components.sonos.sync_get_visible_zones",
            side_effect=[
                OSError(),
                OSError(),
                [],
                [],
                OSError(),
            ],
        ),
    ):
        # First call fails, it should be logged as a WARNING message
        caplog.clear()
        await manager.async_poll_manual_hosts()
        assert len(caplog.messages) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "Could not get visible Sonos devices from" in record.message
        assert mock_async_call_later.call_count == 1

        # Second call fails again, it should be logged as a DEBUG message
        caplog.clear()
        await manager.async_poll_manual_hosts()
        assert len(caplog.messages) == 1
        record = caplog.records[0]
        assert record.levelname == "DEBUG"
        assert "Could not get visible Sonos devices from" in record.message
        assert mock_async_call_later.call_count == 2

        # Third call succeeds, it should log an info message
        caplog.clear()
        await manager.async_poll_manual_hosts()
        assert len(caplog.messages) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "Connection reestablished to Sonos device" in record.message
        assert mock_async_call_later.call_count == 3

        # Fourth call succeeds again, no need to log
        caplog.clear()
        await manager.async_poll_manual_hosts()
        assert len(caplog.messages) == 0
        assert mock_async_call_later.call_count == 4

        # Fifth call fail again again, should be logged as a WARNING message
        caplog.clear()
        await manager.async_poll_manual_hosts()
        assert len(caplog.messages) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "Could not get visible Sonos devices from" in record.message
        assert mock_async_call_later.call_count == 5


class _MockSoCoOsError(MockSoCo):
    @property
    def visible_zones(self):
        raise OSError


class _MockSoCoVisibleZones(MockSoCo):
    def set_visible_zones(self, visible_zones) -> None:
        """Set visible zones."""
        self.vz_return = visible_zones  # pylint: disable=attribute-defined-outside-init

    @property
    def visible_zones(self):
        return self.vz_return


async def _setup_menuai(menuai: menuai):
    await async_setup_component(
        menuai,
        sonos.DOMAIN,
        {
            "sonos": {
                "media_player": {
                    "interface_addr": "127.0.0.1",
                    "hosts": ["10.10.10.1", "10.10.10.2"],
                }
            }
        },
    )
    await menuai.async_block_till_done()


async def test_async_poll_manual_hosts_1(
    menuai: menuai,
    soco_factory: SoCoMockFactory,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests first device fails, second device successful, speakers do not exist."""
    soco_1 = soco_factory.cache_mock(_MockSoCoOsError(), "10.10.10.1", "Living Room")
    soco_2 = soco_factory.cache_mock(MockSoCo(), "10.10.10.2", "Bedroom")

    with caplog.at_level(logging.WARNING):
        await _setup_menuai(menuai)
        assert "media_player.bedroom" in entity_registry.entities
        assert "media_player.living_room" not in entity_registry.entities
        assert (
            f"Could not get visible Sonos devices from {soco_1.ip_address}"
            in caplog.text
        )
        assert (
            f"Could not get visible Sonos devices from {soco_2.ip_address}"
            not in caplog.text
        )

    await menuai.async_block_till_done(wait_background_tasks=True)


async def test_async_poll_manual_hosts_2(
    menuai: menuai,
    soco_factory: SoCoMockFactory,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test first device success, second device fails, speakers do not exist."""
    soco_1 = soco_factory.cache_mock(MockSoCo(), "10.10.10.1", "Living Room")
    soco_2 = soco_factory.cache_mock(_MockSoCoOsError(), "10.10.10.2", "Bedroom")

    with caplog.at_level(logging.WARNING):
        await _setup_menuai(menuai)
        assert "media_player.bedroom" not in entity_registry.entities
        assert "media_player.living_room" in entity_registry.entities
        assert (
            f"Could not get visible Sonos devices from {soco_1.ip_address}"
            not in caplog.text
        )
        assert (
            f"Could not get visible Sonos devices from {soco_2.ip_address}"
            in caplog.text
        )

    await menuai.async_block_till_done(wait_background_tasks=True)


async def test_async_poll_manual_hosts_3(
    menuai: menuai,
    soco_factory: SoCoMockFactory,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test both devices fail, speakers do not exist."""
    soco_1 = soco_factory.cache_mock(_MockSoCoOsError(), "10.10.10.1", "Living Room")
    soco_2 = soco_factory.cache_mock(_MockSoCoOsError(), "10.10.10.2", "Bedroom")

    with caplog.at_level(logging.WARNING):
        await _setup_menuai(menuai)
        assert "media_player.bedroom" not in entity_registry.entities
        assert "media_player.living_room" not in entity_registry.entities
        assert (
            f"Could not get visible Sonos devices from {soco_1.ip_address}"
            in caplog.text
        )
        assert (
            f"Could not get visible Sonos devices from {soco_2.ip_address}"
            in caplog.text
        )

    await menuai.async_block_till_done(wait_background_tasks=True)


async def test_async_poll_manual_hosts_4(
    menuai: menuai,
    soco_factory: SoCoMockFactory,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test both devices are successful, speakers do not exist."""
    soco_1 = soco_factory.cache_mock(MockSoCo(), "10.10.10.1", "Living Room")
    soco_2 = soco_factory.cache_mock(MockSoCo(), "10.10.10.2", "Bedroom")

    with caplog.at_level(logging.WARNING):
        await _setup_menuai(menuai)
        assert "media_player.bedroom" in entity_registry.entities
        assert "media_player.living_room" in entity_registry.entities
        assert (
            f"Could not get visible Sonos devices from {soco_1.ip_address}"
            not in caplog.text
        )
        assert (
            f"Could not get visible Sonos devices from {soco_2.ip_address}"
            not in caplog.text
        )

    await menuai.async_block_till_done(wait_background_tasks=True)


class SpeakerActivity:
    """Unit test class to track speaker activity messages."""

    def __init__(self, menuai: menuai, soco: MockSoCo) -> None:
        """Create the object from soco."""
        self.soco = soco
        self.menuai = menuai
        self.call_count: int = 0
        self.event = asyncio.Event()
        async_dispatcher_connect(
            self.menuai,
            f"{SONOS_SPEAKER_ACTIVITY}-{self.soco.uid}",
            self.speaker_activity,
        )

    @callback
    def speaker_activity(self, source: str) -> None:
        """Track the last activity on this speaker, set availability and resubscribe."""
        if source == "manual zone scan":
            self.event.set()
            self.call_count += 1


async def test_async_poll_manual_hosts_5(
    menuai: menuai,
    soco_factory: SoCoMockFactory,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test both succeed, speakers exist and unavailable, ping succeeds."""
    soco_1 = soco_factory.cache_mock(MockSoCo(), "10.10.10.1", "Living Room")
    soco_1.renderingControl = Mock()
    soco_1.renderingControl.GetVolume = Mock()
    speaker_1_activity = SpeakerActivity(menuai, soco_1)
    soco_2 = soco_factory.cache_mock(MockSoCo(), "10.10.10.2", "Bedroom")
    soco_2.renderingControl = Mock()
    soco_2.renderingControl.GetVolume = Mock()
    speaker_2_activity = SpeakerActivity(menuai, soco_2)
    with patch(
        "menuai.components.sonos.DISCOVERY_INTERVAL"
    ) as mock_discovery_interval:
        # Speed up manual discovery interval so second iteration runs sooner
        mock_discovery_interval.total_seconds = Mock(side_effect=[0.5, 60])

        with caplog.at_level(logging.DEBUG):
            caplog.clear()

            await _setup_menuai(menuai)

            assert "media_player.bedroom" in entity_registry.entities
            assert "media_player.living_room" in entity_registry.entities

            async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=0.5))
            await menuai.async_block_till_done()
            await asyncio.gather(
                *[speaker_1_activity.event.wait(), speaker_2_activity.event.wait()]
            )
            assert speaker_1_activity.call_count == 1
            assert speaker_2_activity.call_count == 1
            assert "Activity on Living Room" in caplog.text
            assert "Activity on Bedroom" in caplog.text

    await menuai.async_block_till_done(wait_background_tasks=True)


async def test_async_poll_manual_hosts_6(
    menuai: menuai,
    soco_factory: SoCoMockFactory,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test both succeed, speakers exist and unavailable, pings fail."""
    soco_1 = soco_factory.cache_mock(MockSoCo(), "10.10.10.1", "Living Room")
    # Rendering Control Get Volume is what speaker ping calls.
    soco_1.renderingControl = Mock()
    soco_1.renderingControl.GetVolume = Mock()
    soco_1.renderingControl.GetVolume.side_effect = SonosUpdateError()
    speaker_1_activity = SpeakerActivity(menuai, soco_1)
    soco_2 = soco_factory.cache_mock(MockSoCo(), "10.10.10.2", "Bedroom")
    soco_2.renderingControl = Mock()
    soco_2.renderingControl.GetVolume = Mock()
    soco_2.renderingControl.GetVolume.side_effect = SonosUpdateError()
    speaker_2_activity = SpeakerActivity(menuai, soco_2)

    with patch(
        "menuai.components.sonos.DISCOVERY_INTERVAL"
    ) as mock_discovery_interval:
        # Speed up manual discovery interval so second iteration runs sooner
        mock_discovery_interval.total_seconds = Mock(side_effect=[0.0, 60])
        await _setup_menuai(menuai)

        assert "media_player.bedroom" in entity_registry.entities
        assert "media_player.living_room" in entity_registry.entities

        with caplog.at_level(logging.DEBUG):
            caplog.clear()
            await menuai.async_block_till_done()
            assert "Activity on Living Room" not in caplog.text
            assert "Activity on Bedroom" not in caplog.text
            assert speaker_1_activity.call_count == 0
            assert speaker_2_activity.call_count == 0

    await menuai.async_block_till_done(wait_background_tasks=True)


async def test_async_poll_manual_hosts_7(
    menuai: menuai,
    soco_factory: SoCoMockFactory,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test both succeed, speaker do not exist, new hosts found in visible zones."""
    soco_1 = soco_factory.cache_mock(
        _MockSoCoVisibleZones(), "10.10.10.1", "Living Room"
    )
    soco_2 = soco_factory.cache_mock(_MockSoCoVisibleZones(), "10.10.10.2", "Bedroom")
    soco_3 = soco_factory.cache_mock(MockSoCo(), "10.10.10.3", "Basement")
    soco_4 = soco_factory.cache_mock(MockSoCo(), "10.10.10.4", "Garage")
    soco_5 = soco_factory.cache_mock(MockSoCo(), "10.10.10.5", "Studio")

    soco_1.set_visible_zones({soco_1, soco_2, soco_3, soco_4, soco_5})
    soco_2.set_visible_zones({soco_1, soco_2, soco_3, soco_4, soco_5})

    await _setup_menuai(menuai)
    await menuai.async_block_till_done()

    assert "media_player.bedroom" in entity_registry.entities
    assert "media_player.living_room" in entity_registry.entities
    assert "media_player.basement" in entity_registry.entities
    assert "media_player.garage" in entity_registry.entities
    assert "media_player.studio" in entity_registry.entities

    await menuai.async_block_till_done(wait_background_tasks=True)


async def test_async_poll_manual_hosts_8(
    menuai: menuai,
    soco_factory: SoCoMockFactory,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test both succeed, speaker do not exist, invisible zone."""
    soco_1 = soco_factory.cache_mock(
        _MockSoCoVisibleZones(), "10.10.10.1", "Living Room"
    )
    soco_2 = soco_factory.cache_mock(_MockSoCoVisibleZones(), "10.10.10.2", "Bedroom")
    soco_3 = soco_factory.cache_mock(MockSoCo(), "10.10.10.3", "Basement")
    soco_4 = soco_factory.cache_mock(MockSoCo(), "10.10.10.4", "Garage")
    soco_5 = soco_factory.cache_mock(MockSoCo(), "10.10.10.5", "Studio")

    soco_1.set_visible_zones({soco_2, soco_3, soco_4, soco_5})
    soco_2.set_visible_zones({soco_2, soco_3, soco_4, soco_5})

    await _setup_menuai(menuai)
    await menuai.async_block_till_done()

    assert "media_player.bedroom" in entity_registry.entities
    assert "media_player.living_room" not in entity_registry.entities
    assert "media_player.basement" in entity_registry.entities
    assert "media_player.garage" in entity_registry.entities
    assert "media_player.studio" in entity_registry.entities
    await menuai.async_block_till_done(wait_background_tasks=True)


async def _setup_menuai_ipv6_address_not_supported(menuai: menuai):
    await async_setup_component(
        menuai,
        sonos.DOMAIN,
        {
            "sonos": {
                "media_player": {
                    "interface_addr": "127.0.0.1",
                    "hosts": ["2001:db8:3333:4444:5555:6666:7777:8888"],
                }
            }
        },
    )
    await menuai.async_block_till_done()


async def test_ipv6_not_supported(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Tests that invalid ipv4 addresses do not generate stack dump."""
    with caplog.at_level(logging.DEBUG):
        caplog.clear()
        await _setup_menuai_ipv6_address_not_supported(menuai)
        await menuai.async_block_till_done()
    assert "invalid ip_address received" in caplog.text
    assert "2001:db8:3333:4444:5555:6666:7777:8888" in caplog.text
