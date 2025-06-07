"""Test squeezebox update platform."""

import copy
from datetime import timedelta
from unittest.mock import patch

import pytest

from menuai.components.squeezebox.const import (
    SENSOR_UPDATE_INTERVAL,
    STATUS_UPDATE_NEWPLUGINS,
)
from menuai.components.update import (
    ATTR_IN_PROGRESS,
    DOMAIN as UPDATE_DOMAIN,
    SERVICE_INSTALL,
)
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.util import dt as dt_util

from .conftest import FAKE_QUERY_RESPONSE

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_update_lms(
    menuai: menuai,
    config_entry: MockConfigEntry,
) -> None:
    """Test binary sensor states and attributes."""

    # Setup component
    with (
        patch(
            "menuai.components.squeezebox.PLATFORMS",
            [Platform.UPDATE],
        ),
        patch(
            "menuai.components.squeezebox.Server.async_query",
            return_value=copy.deepcopy(FAKE_QUERY_RESPONSE),
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done(wait_background_tasks=True)
    state = menuai.states.get("update.fakelib_lyrion_music_server")

    assert state is not None
    assert state.state == STATE_ON


async def test_update_plugins_install_fallback(
    menuai: menuai,
    config_entry: MockConfigEntry,
) -> None:
    """Test binary sensor states and attributes."""

    entity_id = "update.fakelib_updated_plugins"
    # Setup component
    with (
        patch(
            "menuai.components.squeezebox.PLATFORMS",
            [Platform.UPDATE],
        ),
        patch(
            "menuai.components.squeezebox.Server.async_query",
            return_value=copy.deepcopy(FAKE_QUERY_RESPONSE),
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_ON

    polltime = 30
    with (
        patch(
            "menuai.components.squeezebox.Server.async_query",
            return_value=False,
        ),
        patch(
            "menuai.components.squeezebox.update.POLL_AFTER_INSTALL",
            polltime,
        ),
    ):
        await menuai.services.async_call(
            UPDATE_DOMAIN,
            SERVICE_INSTALL,
            {
                ATTR_ENTITY_ID: entity_id,
            },
            blocking=True,
        )

    state = menuai.states.get(entity_id)
    attrs = state.attributes
    assert attrs[ATTR_IN_PROGRESS]

    with (
        patch(
            "menuai.components.squeezebox.Server.async_status",
            return_value=copy.deepcopy(FAKE_QUERY_RESPONSE),
        ),
    ):
        async_fire_time_changed(
            menuai,
            dt_util.utcnow() + timedelta(seconds=polltime + 1),
        )
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_ON

    attrs = state.attributes
    assert not attrs[ATTR_IN_PROGRESS]


async def test_update_plugins_install_restart_fail(
    menuai: menuai,
    config_entry: MockConfigEntry,
) -> None:
    """Test binary sensor states and attributes."""

    entity_id = "update.fakelib_updated_plugins"
    # Setup component
    with (
        patch(
            "menuai.components.squeezebox.PLATFORMS",
            [Platform.UPDATE],
        ),
        patch(
            "menuai.components.squeezebox.Server.async_query",
            return_value=copy.deepcopy(FAKE_QUERY_RESPONSE),
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done(wait_background_tasks=True)

    with (
        patch(
            "menuai.components.squeezebox.Server.async_query",
            return_value=True,
        ),
        pytest.raises(menuaiError),
    ):
        await menuai.services.async_call(
            UPDATE_DOMAIN,
            SERVICE_INSTALL,
            {
                ATTR_ENTITY_ID: entity_id,
            },
            blocking=True,
        )
    state = menuai.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_ON

    attrs = state.attributes
    assert not attrs[ATTR_IN_PROGRESS]


async def test_update_plugins_install_ok(
    menuai: menuai,
    config_entry: MockConfigEntry,
) -> None:
    """Test binary sensor states and attributes."""

    entity_id = "update.fakelib_updated_plugins"
    # Setup component
    with (
        patch(
            "menuai.components.squeezebox.PLATFORMS",
            [Platform.UPDATE],
        ),
        patch(
            "menuai.components.squeezebox.Server.async_query",
            return_value=copy.deepcopy(FAKE_QUERY_RESPONSE),
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done(wait_background_tasks=True)

    with (
        patch(
            "menuai.components.squeezebox.Server.async_query",
            return_value=False,
        ),
    ):
        await menuai.services.async_call(
            UPDATE_DOMAIN,
            SERVICE_INSTALL,
            {
                ATTR_ENTITY_ID: entity_id,
            },
            blocking=True,
        )
    state = menuai.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_ON

    attrs = state.attributes
    assert attrs[ATTR_IN_PROGRESS]

    resp = copy.deepcopy(FAKE_QUERY_RESPONSE)
    del resp[STATUS_UPDATE_NEWPLUGINS]

    with (
        patch(
            "menuai.components.squeezebox.Server.async_status",
            return_value=resp,
        ),
        patch(
            "menuai.components.squeezebox.Server.async_query",
            return_value=copy.deepcopy(FAKE_QUERY_RESPONSE),
        ),
    ):
        async_fire_time_changed(
            menuai,
            dt_util.utcnow() + timedelta(seconds=SENSOR_UPDATE_INTERVAL + 1),
        )
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_OFF

    attrs = state.attributes
    assert not attrs[ATTR_IN_PROGRESS]
