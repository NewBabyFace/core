"""The tests for the TTS component."""

from unittest.mock import patch

import pytest

from menuai.components import notify, tts
from menuai.components.media_player import (
    DOMAIN as DOMAIN_MP,
    SERVICE_PLAY_MEDIA,
)
from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config
from menuai.setup import async_setup_component

from .common import MockTTSEntity, mock_config_entry_setup

from tests.common import assert_setup_component, async_mock_service


@pytest.fixture(autouse=True)
async def internal_url_mock(menuai: menuai) -> None:
    """Mock internal URL of the instance."""
    await async_process_ha_core_config(
        menuai,
        {"internal_url": "http://example.local:8123"},
    )


@pytest.fixture(autouse=True)
async def disable_platforms() -> None:
    """Disable demo platforms."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [],
    ):
        yield


async def test_setup_legacy_platform(menuai: menuai) -> None:
    """Set up the tts notify platform ."""
    config = {
        notify.DOMAIN: {
            "platform": "tts",
            "name": "tts_test",
            "tts_service": "tts.demo_say",
            "media_player": "media_player.demo",
        }
    }
    with assert_setup_component(1, notify.DOMAIN):
        assert await async_setup_component(menuai, notify.DOMAIN, config)
        await menuai.async_block_till_done()

    assert menuai.services.has_service(notify.DOMAIN, "tts_test")


async def test_setup_platform(menuai: menuai) -> None:
    """Set up the tts notify platform ."""
    config = {
        notify.DOMAIN: {
            "platform": "tts",
            "name": "tts_test",
            "entity_id": "tts.test",
            "media_player": "media_player.demo",
        }
    }
    with assert_setup_component(1, notify.DOMAIN):
        assert await async_setup_component(menuai, notify.DOMAIN, config)
        await menuai.async_block_till_done()

    assert menuai.services.has_service(notify.DOMAIN, "tts_test")


async def test_setup_platform_missing_key(menuai: menuai) -> None:
    """Test platform without required tts_service or entity_id key."""
    config = {
        notify.DOMAIN: {
            "platform": "tts",
            "name": "tts_test",
            "media_player": "media_player.demo",
        }
    }
    with assert_setup_component(0, notify.DOMAIN):
        assert await async_setup_component(menuai, notify.DOMAIN, config)
        await menuai.async_block_till_done()

    assert not menuai.services.has_service(notify.DOMAIN, "tts_test")


async def test_setup_legacy_service(menuai: menuai) -> None:
    """Set up the demo platform and call service."""
    calls = async_mock_service(menuai, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    config = {
        tts.DOMAIN: {"platform": "demo"},
        notify.DOMAIN: {
            "platform": "tts",
            "name": "tts_test",
            "tts_service": "tts.demo_say",
            "media_player": "media_player.demo",
            "language": "en",
        },
    }

    await async_setup_component(menuai, "menuai", {})

    with assert_setup_component(1, tts.DOMAIN):
        assert await async_setup_component(menuai, tts.DOMAIN, config)

    with assert_setup_component(1, notify.DOMAIN):
        assert await async_setup_component(menuai, notify.DOMAIN, config)

    await menuai.async_block_till_done()

    await menuai.services.async_call(
        notify.DOMAIN,
        "tts_test",
        {
            tts.ATTR_MESSAGE: "There is someone at the door.",
        },
        blocking=True,
    )

    await menuai.async_block_till_done()

    assert len(calls) == 1


async def test_setup_service(
    menuai: menuai, mock_tts_entity: MockTTSEntity
) -> None:
    """Set up platform and call service."""
    calls = async_mock_service(menuai, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    config = {
        notify.DOMAIN: {
            "platform": "tts",
            "name": "tts_test",
            "entity_id": "tts.test",
            "media_player": "media_player.demo",
            "language": "en_US",
        },
    }

    await mock_config_entry_setup(menuai, mock_tts_entity)

    with assert_setup_component(1, notify.DOMAIN):
        assert await async_setup_component(menuai, notify.DOMAIN, config)

    await menuai.async_block_till_done()

    await menuai.services.async_call(
        notify.DOMAIN,
        "tts_test",
        {
            tts.ATTR_MESSAGE: "There is someone at the door.",
        },
        blocking=True,
    )

    await menuai.async_block_till_done()

    assert len(calls) == 1
