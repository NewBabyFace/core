"""Sensor tests for the YouTube integration."""

import asyncio
from datetime import timedelta
from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion
from youtubeaio.types import UnauthorizedError, YouTubeBackendError

from menuai import config_entries
from menuai.components.youtube.const import DOMAIN
from menuai.core import menuai
from menuai.util import dt as dt_util

from . import MockYouTube
from .conftest import ComponentSetup

from tests.common import async_fire_time_changed


async def test_sensor(
    menuai: menuai, snapshot: SnapshotAssertion, setup_integration: ComponentSetup
) -> None:
    """Test sensor."""
    await setup_integration()

    state = menuai.states.get("sensor.google_for_developers_latest_upload")
    assert state == snapshot

    state = menuai.states.get("sensor.google_for_developers_subscribers")
    assert state == snapshot

    state = menuai.states.get("sensor.google_for_developers_views")
    assert state == snapshot


async def test_sensor_without_uploaded_video(
    menuai: menuai, snapshot: SnapshotAssertion, setup_integration: ComponentSetup
) -> None:
    """Test sensor when there is no video on the channel."""
    await setup_integration()

    with patch(
        "menuai.components.youtube.api.AsyncConfigEntryAuth.get_resource",
        return_value=MockYouTube(
            menuai, playlist_items_fixture="get_no_playlist_items.json"
        ),
    ):
        future = dt_util.utcnow() + timedelta(minutes=15)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()
        await asyncio.sleep(0.1)

    state = menuai.states.get("sensor.google_for_developers_latest_upload")
    assert state == snapshot

    state = menuai.states.get("sensor.google_for_developers_subscribers")
    assert state == snapshot

    state = menuai.states.get("sensor.google_for_developers_views")
    assert state == snapshot


async def test_sensor_updating(
    menuai: menuai, setup_integration: ComponentSetup
) -> None:
    """Test updating sensor."""
    await setup_integration()

    state = menuai.states.get("sensor.google_for_developers_latest_upload")
    assert state
    assert state.attributes["video_id"] == "wysukDrMdqU"

    with patch(
        "menuai.components.youtube.api.AsyncConfigEntryAuth.get_resource",
        return_value=MockYouTube(
            menuai, playlist_items_fixture="get_playlist_items_2.json"
        ),
    ):
        future = dt_util.utcnow() + timedelta(minutes=15)
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()
        await asyncio.sleep(0.1)
    state = menuai.states.get("sensor.google_for_developers_latest_upload")
    assert state
    assert state.name == "Google for Developers Latest upload"
    assert state.state == "Google I/O 2023 Developer Keynote in 5 minutes"
    assert (
        state.attributes["entity_picture"]
        == "https://i.ytimg.com/vi/hleLlcHwQLM/maxresdefault.jpg"
    )
    assert state.attributes["video_id"] == "hleLlcHwQLM"


async def test_sensor_reauth_trigger(
    menuai: menuai, setup_integration: ComponentSetup
) -> None:
    """Test reauth is triggered after a refresh error."""
    mock = await setup_integration()

    state = menuai.states.get("sensor.google_for_developers_latest_upload")
    assert state.state == "What's new in Google Home in less than 1 minute"

    state = menuai.states.get("sensor.google_for_developers_subscribers")
    assert state.state == "2290000"

    state = menuai.states.get("sensor.google_for_developers_views")
    assert state.state == "214141263"

    mock.set_thrown_exception(UnauthorizedError())
    future = dt_util.utcnow() + timedelta(minutes=15)
    async_fire_time_changed(menuai, future)
    await menuai.async_block_till_done()

    flows = menuai.config_entries.flow.async_progress()

    assert len(flows) == 1
    flow = flows[0]
    assert flow["step_id"] == "reauth_confirm"
    assert flow["handler"] == DOMAIN
    assert flow["context"]["source"] == config_entries.SOURCE_REAUTH


async def test_sensor_unavailable(
    menuai: menuai, setup_integration: ComponentSetup
) -> None:
    """Test update failed."""
    mock = await setup_integration()

    state = menuai.states.get("sensor.google_for_developers_latest_upload")
    assert state.state == "What's new in Google Home in less than 1 minute"

    state = menuai.states.get("sensor.google_for_developers_subscribers")
    assert state.state == "2290000"

    state = menuai.states.get("sensor.google_for_developers_views")
    assert state.state == "214141263"

    mock.set_thrown_exception(YouTubeBackendError())
    future = dt_util.utcnow() + timedelta(minutes=15)
    async_fire_time_changed(menuai, future)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.google_for_developers_latest_upload")
    assert state.state == "unavailable"

    state = menuai.states.get("sensor.google_for_developers_subscribers")
    assert state.state == "unavailable"

    state = menuai.states.get("sensor.google_for_developers_views")
    assert state.state == "unavailable"
