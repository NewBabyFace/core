"""The test for the Yale Smart ALarm lock platform."""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import Mock

import pytest
from syrupy.assertion import SnapshotAssertion
from yalesmartalarmclient import UnknownError, YaleDoorManAPI, YaleSmartAlarmData

from menuai.components.lock import DOMAIN as LOCK_DOMAIN
from menuai.const import (
    ATTR_CODE,
    ATTR_ENTITY_ID,
    SERVICE_LOCK,
    SERVICE_UNLOCK,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.parametrize(
    "load_platforms",
    [[Platform.LOCK]],
)
async def test_lock(
    menuai: menuai,
    load_config_entry: tuple[MockConfigEntry, Mock],
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Yale Smart Alarm lock."""
    entry = load_config_entry[0]
    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


@pytest.mark.parametrize(
    "load_platforms",
    [[Platform.LOCK]],
)
async def test_lock_service_calls(
    menuai: menuai,
    get_data: YaleSmartAlarmData,
    load_config_entry: tuple[MockConfigEntry, Mock],
) -> None:
    """Test the Yale Smart Alarm lock."""

    client = load_config_entry[1]

    data = deepcopy(get_data.cycle)
    data["data"] = data["data"].pop("device_status")

    client.auth.get_authenticated = Mock(return_value=data)
    client.auth.post_authenticated = Mock(return_value={"code": "000"})
    client.lock_api = YaleDoorManAPI(client.auth)

    state = menuai.states.get("lock.device1")
    assert state.state == "locked"

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_UNLOCK,
            {ATTR_ENTITY_ID: "lock.device1"},
            blocking=True,
        )

    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_UNLOCK,
        {ATTR_ENTITY_ID: "lock.device1", ATTR_CODE: "123456"},
        blocking=True,
    )
    client.auth.post_authenticated.assert_called_once()
    state = menuai.states.get("lock.device1")
    assert state.state == "unlocked"
    client.auth.post_authenticated.reset_mock()
    await menuai.services.async_call(
        LOCK_DOMAIN,
        SERVICE_LOCK,
        {ATTR_ENTITY_ID: "lock.device1", ATTR_CODE: "123456"},
        blocking=True,
    )
    client.auth.post_authenticated.assert_called_once()
    state = menuai.states.get("lock.device1")
    assert state.state == "locked"


@pytest.mark.parametrize(
    "load_platforms",
    [[Platform.LOCK]],
)
async def test_lock_service_call_fails(
    menuai: menuai,
    get_data: YaleSmartAlarmData,
    load_config_entry: tuple[MockConfigEntry, Mock],
) -> None:
    """Test the Yale Smart Alarm lock service call fails."""

    client = load_config_entry[1]

    data = deepcopy(get_data.cycle)
    data["data"] = data["data"].pop("device_status")

    client.auth.get_authenticated = Mock(return_value=data)
    client.auth.post_authenticated = Mock(side_effect=UnknownError("test_side_effect"))
    client.lock_api = YaleDoorManAPI(client.auth)

    state = menuai.states.get("lock.device1")
    assert state.state == "locked"

    with pytest.raises(
        menuaiError,
        match="Could not set lock for Device1: test_side_effect",
    ):
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_UNLOCK,
            {ATTR_ENTITY_ID: "lock.device1", ATTR_CODE: "123456"},
            blocking=True,
        )
    client.auth.post_authenticated.assert_called_once()
    state = menuai.states.get("lock.device1")
    assert state.state == "locked"
    client.auth.post_authenticated.reset_mock()
    with pytest.raises(
        menuaiError,
        match="Could not set lock for Device1: test_side_effect",
    ):
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_LOCK,
            {ATTR_ENTITY_ID: "lock.device1", ATTR_CODE: "123456"},
            blocking=True,
        )
    client.auth.post_authenticated.assert_called_once()


@pytest.mark.parametrize(
    "load_platforms",
    [[Platform.LOCK]],
)
async def test_lock_service_call_fails_with_incorrect_status(
    menuai: menuai,
    get_data: YaleSmartAlarmData,
    load_config_entry: tuple[MockConfigEntry, Mock],
) -> None:
    """Test the Yale Smart Alarm lock service call fails with incorrect return state."""

    client = load_config_entry[1]

    data = deepcopy(get_data.cycle)
    data["data"] = data["data"].pop("device_status")

    client.auth.post_authenticated = Mock(return_value={"code": "FFF"})

    state = menuai.states.get("lock.device1")
    assert state.state == "locked"

    with pytest.raises(
        menuaiError, match="Could not set lock, check system ready for lock"
    ):
        await menuai.services.async_call(
            LOCK_DOMAIN,
            SERVICE_UNLOCK,
            {ATTR_ENTITY_ID: "lock.device1", ATTR_CODE: "123456"},
            blocking=True,
        )
    client.auth.post_authenticated.assert_called_once()
    state = menuai.states.get("lock.device1")
    assert state.state == "locked"
