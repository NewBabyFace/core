"""Test BMW locks."""

from unittest.mock import AsyncMock, patch

from bimmer_connected.models import MyBMWRemoteServiceError
from bimmer_connected.vehicle.remote_services import RemoteServices
from freezegun import freeze_time
import pytest
import respx
from syrupy.assertion import SnapshotAssertion

from menuai.components.recorder.history import get_significant_states
from menuai.const import STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from . import (
    REMOTE_SERVICE_EXC_REASON,
    REMOTE_SERVICE_EXC_TRANSLATION,
    check_remote_service_call,
    setup_mocked_integration,
)

from tests.common import snapshot_platform
from tests.components.recorder.common import async_wait_recording_done


@freeze_time("2023-06-22 10:30:00+00:00")
@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_entity_state_attrs(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test lock states and attributes."""

    # Setup component
    with patch(
        "menuai.components.bmw_connected_drive.PLATFORMS", [Platform.LOCK]
    ):
        mock_config_entry = await setup_mocked_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.usefixtures("recorder_mock")
@pytest.mark.parametrize(
    ("entity_id", "new_value", "old_value", "service", "remote_service"),
    [
        (
            "lock.m340i_xdrive_lock",
            "locked",
            "unlocked",
            "lock",
            "door-lock",
        ),
        ("lock.m340i_xdrive_lock", "unlocked", "locked", "unlock", "door-unlock"),
    ],
)
async def test_service_call_success(
    menuai: menuai,
    entity_id: str,
    new_value: str,
    old_value: str,
    service: str,
    remote_service: str,
    bmw_fixture: respx.Router,
) -> None:
    """Test successful service call."""

    # Setup component
    assert await setup_mocked_integration(menuai)
    menuai.states.async_set(entity_id, old_value)
    assert menuai.states.get(entity_id).state == old_value

    now = dt_util.utcnow()

    # Test
    await menuai.services.async_call(
        "lock",
        service,
        blocking=True,
        target={"entity_id": entity_id},
    )
    check_remote_service_call(bmw_fixture, remote_service)
    assert menuai.states.get(entity_id).state == new_value

    # wait for the recorder to really store the data
    await async_wait_recording_done(menuai)
    states = await menuai.async_add_executor_job(
        get_significant_states, menuai, now, None, [entity_id]
    )
    assert any(s for s in states[entity_id] if s.state == STATE_UNKNOWN) is False


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("recorder_mock")
@pytest.mark.parametrize(
    ("entity_id", "service"),
    [
        ("lock.m340i_xdrive_lock", "lock"),
        ("lock.m340i_xdrive_lock", "unlock"),
    ],
)
async def test_service_call_fail(
    menuai: menuai,
    entity_id: str,
    service: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test failed service call."""

    # Setup component
    assert await setup_mocked_integration(menuai)
    old_value = menuai.states.get(entity_id).state

    now = dt_util.utcnow()

    # Setup exception
    monkeypatch.setattr(
        RemoteServices,
        "trigger_remote_service",
        AsyncMock(side_effect=MyBMWRemoteServiceError(REMOTE_SERVICE_EXC_REASON)),
    )

    # Test
    with pytest.raises(menuaiError, match=REMOTE_SERVICE_EXC_TRANSLATION):
        await menuai.services.async_call(
            "lock",
            service,
            blocking=True,
            target={"entity_id": entity_id},
        )
    assert menuai.states.get(entity_id).state == old_value

    # wait for the recorder to really store the data
    await async_wait_recording_done(menuai)
    states = await menuai.async_add_executor_job(
        get_significant_states, menuai, now, None, [entity_id]
    )
    assert states[entity_id][-2].state == STATE_UNKNOWN
