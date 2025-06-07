"""Test the pjlink media player platform."""

from datetime import timedelta
import socket
from unittest.mock import create_autospec, patch

import pypjlink
from pypjlink import MUTE_AUDIO
from pypjlink.projector import ProjectorError
import pytest

from menuai.components import media_player
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import assert_setup_component, async_fire_time_changed


@pytest.fixture(name="projector_from_address")
def projector_from_address():
    """Create pjlink Projector mock."""

    with patch("pypjlink.Projector.from_address") as from_address:
        constructor = create_autospec(pypjlink.Projector)
        from_address.return_value = constructor.return_value
        yield from_address


@pytest.fixture(name="mocked_projector")
def mocked_projector(projector_from_address):
    """Create pjlink Projector instance mock."""

    instance = projector_from_address.return_value

    with instance as mocked_instance:
        mocked_instance.get_name.return_value = "Test"
        mocked_instance.get_power.return_value = "on"
        mocked_instance.get_mute.return_value = [0, True]
        mocked_instance.get_input.return_value = [0, 1]
        mocked_instance.get_inputs.return_value = (
            ("HDMI", 1),
            ("HDMI", 2),
            ("VGA", 1),
        )

        yield mocked_instance


@pytest.mark.parametrize("side_effect", [socket.timeout, OSError])
async def test_offline_initialization(
    projector_from_address, menuai: menuai, side_effect
) -> None:
    """Test initialization of a device that is offline."""

    with assert_setup_component(1, media_player.DOMAIN):
        projector_from_address.side_effect = side_effect

        assert await async_setup_component(
            menuai,
            media_player.DOMAIN,
            {
                media_player.DOMAIN: {
                    "platform": "pjlink",
                    "name": "test_offline",
                    "host": "127.0.0.1",
                }
            },
        )
        await menuai.async_block_till_done()

        state = menuai.states.get("media_player.test_offline")
        assert state.state == "unavailable"


async def test_initialization(projector_from_address, menuai: menuai) -> None:
    """Test a device that is available."""

    with assert_setup_component(1, media_player.DOMAIN):
        instance = projector_from_address.return_value

        with instance as mocked_instance:
            mocked_instance.get_name.return_value = "Test"
            mocked_instance.get_inputs.return_value = (
                ("HDMI", 1),
                ("HDMI", 2),
                ("VGA", 1),
            )

        assert await async_setup_component(
            menuai,
            media_player.DOMAIN,
            {
                media_player.DOMAIN: {
                    "platform": "pjlink",
                    "host": "127.0.0.1",
                }
            },
        )

        await menuai.async_block_till_done()

        state = menuai.states.get("media_player.test")
        assert state.state == "off"

        assert "source_list" in state.attributes
        source_list = state.attributes["source_list"]

        assert set(source_list) == {"HDMI 1", "HDMI 2", "VGA 1"}


@pytest.mark.parametrize("power_state", ["on", "warm-up"])
async def test_on_state_init(
    projector_from_address, menuai: menuai, power_state
) -> None:
    """Test a device that is available."""

    with assert_setup_component(1, media_player.DOMAIN):
        instance = projector_from_address.return_value

        with instance as mocked_instance:
            mocked_instance.get_name.return_value = "Test"
            mocked_instance.get_power.return_value = power_state
            mocked_instance.get_inputs.return_value = (("HDMI", 1),)
            mocked_instance.get_input.return_value = ("HDMI", 1)

        assert await async_setup_component(
            menuai,
            media_player.DOMAIN,
            {
                media_player.DOMAIN: {
                    "platform": "pjlink",
                    "host": "127.0.0.1",
                }
            },
        )

        await menuai.async_block_till_done()

        state = menuai.states.get("media_player.test")
        assert state.state == "on"

        assert state.attributes["source"] == "HDMI 1"


async def test_api_error(projector_from_address, menuai: menuai) -> None:
    """Test invalid api responses."""

    with assert_setup_component(1, media_player.DOMAIN):
        instance = projector_from_address.return_value

        with instance as mocked_instance:
            mocked_instance.get_name.return_value = "Test"
            mocked_instance.get_inputs.return_value = (
                ("HDMI", 1),
                ("HDMI", 2),
                ("VGA", 1),
            )
            mocked_instance.get_power.side_effect = KeyError("OK")

        assert await async_setup_component(
            menuai,
            media_player.DOMAIN,
            {
                media_player.DOMAIN: {
                    "platform": "pjlink",
                    "host": "127.0.0.1",
                }
            },
        )

        await menuai.async_block_till_done()

        state = menuai.states.get("media_player.test")
        assert state.state == "off"


async def test_update_unavailable(projector_from_address, menuai: menuai) -> None:
    """Test update to a device that is unavailable."""

    with assert_setup_component(1, media_player.DOMAIN):
        instance = projector_from_address.return_value

        with instance as mocked_instance:
            mocked_instance.get_name.return_value = "Test"
            mocked_instance.get_inputs.return_value = (
                ("HDMI", 1),
                ("HDMI", 2),
                ("VGA", 1),
            )

        assert await async_setup_component(
            menuai,
            media_player.DOMAIN,
            {
                media_player.DOMAIN: {
                    "platform": "pjlink",
                    "host": "127.0.0.1",
                }
            },
        )

        await menuai.async_block_till_done()

        state = menuai.states.get("media_player.test")
        assert state.state == "off"

        projector_from_address.side_effect = socket.timeout
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
        await menuai.async_block_till_done(wait_background_tasks=True)

        state = menuai.states.get("media_player.test")
        assert state.state == "unavailable"


async def test_unavailable_time(mocked_projector, menuai: menuai) -> None:
    """Test unavailable time projector error."""

    assert await async_setup_component(
        menuai,
        media_player.DOMAIN,
        {
            media_player.DOMAIN: {
                "platform": "pjlink",
                "host": "127.0.0.1",
            }
        },
    )

    await menuai.async_block_till_done()

    state = menuai.states.get("media_player.test")
    assert state.state == "on"
    assert state.attributes["source"] is not None
    assert state.attributes["is_volume_muted"] is not False

    mocked_projector.get_power.side_effect = ProjectorError("unavailable time")
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=10))
    await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("media_player.test")
    assert state.state == "off"
    assert "source" not in state.attributes
    assert "is_volume_muted" not in state.attributes


async def test_turn_off(mocked_projector, menuai: menuai) -> None:
    """Test turning off beamer."""

    assert await async_setup_component(
        menuai,
        media_player.DOMAIN,
        {
            media_player.DOMAIN: {
                "platform": "pjlink",
                "host": "127.0.0.1",
            }
        },
    )

    await menuai.async_block_till_done()
    await menuai.services.async_call(
        domain=media_player.DOMAIN,
        service="turn_off",
        service_data={ATTR_ENTITY_ID: "media_player.test"},
        blocking=True,
    )

    mocked_projector.set_power.assert_called_with("off")


async def test_turn_on(mocked_projector, menuai: menuai) -> None:
    """Test turning on beamer."""

    assert await async_setup_component(
        menuai,
        media_player.DOMAIN,
        {
            media_player.DOMAIN: {
                "platform": "pjlink",
                "host": "127.0.0.1",
            }
        },
    )

    await menuai.async_block_till_done()
    await menuai.services.async_call(
        domain=media_player.DOMAIN,
        service="turn_on",
        service_data={ATTR_ENTITY_ID: "media_player.test"},
        blocking=True,
    )

    mocked_projector.set_power.assert_called_with("on")


async def test_mute(mocked_projector, menuai: menuai) -> None:
    """Test muting beamer."""

    assert await async_setup_component(
        menuai,
        media_player.DOMAIN,
        {
            media_player.DOMAIN: {
                "platform": "pjlink",
                "host": "127.0.0.1",
            }
        },
    )

    await menuai.async_block_till_done()
    await menuai.services.async_call(
        domain=media_player.DOMAIN,
        service="volume_mute",
        service_data={ATTR_ENTITY_ID: "media_player.test", "is_volume_muted": True},
        blocking=True,
    )

    mocked_projector.set_mute.assert_called_with(MUTE_AUDIO, True)


async def test_unmute(mocked_projector, menuai: menuai) -> None:
    """Test unmuting beamer."""

    assert await async_setup_component(
        menuai,
        media_player.DOMAIN,
        {
            media_player.DOMAIN: {
                "platform": "pjlink",
                "host": "127.0.0.1",
            }
        },
    )

    await menuai.async_block_till_done()
    await menuai.services.async_call(
        domain=media_player.DOMAIN,
        service="volume_mute",
        service_data={ATTR_ENTITY_ID: "media_player.test", "is_volume_muted": False},
        blocking=True,
    )

    mocked_projector.set_mute.assert_called_with(MUTE_AUDIO, False)


async def test_select_source(mocked_projector, menuai: menuai) -> None:
    """Test selecting source."""

    assert await async_setup_component(
        menuai,
        media_player.DOMAIN,
        {
            media_player.DOMAIN: {
                "platform": "pjlink",
                "host": "127.0.0.1",
            }
        },
    )

    await menuai.async_block_till_done()
    await menuai.services.async_call(
        domain=media_player.DOMAIN,
        service="select_source",
        service_data={ATTR_ENTITY_ID: "media_player.test", "source": "VGA 1"},
        blocking=True,
    )

    mocked_projector.set_input.assert_called_with("VGA", 1)
