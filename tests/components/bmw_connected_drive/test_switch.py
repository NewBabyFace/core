"""Test BMW switches."""

from unittest.mock import AsyncMock, patch

from bimmer_connected.models import MyBMWAPIError, MyBMWRemoteServiceError
from bimmer_connected.vehicle.remote_services import RemoteServices
import pytest
import respx
from syrupy.assertion import SnapshotAssertion

from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import (
    REMOTE_SERVICE_EXC_REASON,
    REMOTE_SERVICE_EXC_TRANSLATION,
    check_remote_service_call,
    setup_mocked_integration,
)

from tests.common import snapshot_platform


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_entity_state_attrs(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test switch options and values.."""

    # Setup component
    with patch(
        "menuai.components.bmw_connected_drive.PLATFORMS",
        [Platform.SWITCH],
    ):
        mock_config_entry = await setup_mocked_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "new_value", "old_value", "remote_service", "remote_service_params"),
    [
        ("switch.i4_edrive40_climate", "on", "off", "climate-now", {"action": "START"}),
        ("switch.i4_edrive40_climate", "off", "on", "climate-now", {"action": "STOP"}),
        ("switch.iX_xdrive50_charging", "on", "off", "start-charging", {}),
        ("switch.iX_xdrive50_charging", "off", "on", "stop-charging", {}),
    ],
)
async def test_service_call_success(
    menuai: menuai,
    entity_id: str,
    new_value: str,
    old_value: str,
    remote_service: str,
    remote_service_params: dict,
    bmw_fixture: respx.Router,
) -> None:
    """Test successful switch change."""

    # Setup component
    assert await setup_mocked_integration(menuai)
    menuai.states.async_set(entity_id, old_value)
    assert menuai.states.get(entity_id).state == old_value

    # Test
    await menuai.services.async_call(
        "switch",
        f"turn_{new_value}",
        blocking=True,
        target={"entity_id": entity_id},
    )
    check_remote_service_call(bmw_fixture, remote_service, remote_service_params)
    assert menuai.states.get(entity_id).state == new_value


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.parametrize(
    ("raised", "expected", "exc_translation"),
    [
        (
            MyBMWRemoteServiceError(REMOTE_SERVICE_EXC_REASON),
            menuaiError,
            REMOTE_SERVICE_EXC_TRANSLATION,
        ),
        (
            MyBMWAPIError(REMOTE_SERVICE_EXC_REASON),
            menuaiError,
            REMOTE_SERVICE_EXC_TRANSLATION,
        ),
    ],
)
async def test_service_call_fail(
    menuai: menuai,
    raised: Exception,
    expected: Exception,
    exc_translation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test exception handling."""

    # Setup component
    assert await setup_mocked_integration(menuai)
    entity_id = "switch.i4_edrive40_climate"

    # Setup exception
    monkeypatch.setattr(
        RemoteServices,
        "trigger_remote_service",
        AsyncMock(side_effect=raised),
    )

    # Turning switch to ON
    old_value = "off"
    menuai.states.async_set(entity_id, old_value)
    assert menuai.states.get(entity_id).state == old_value

    # Test
    with pytest.raises(expected, match=exc_translation):
        await menuai.services.async_call(
            "switch",
            "turn_on",
            blocking=True,
            target={"entity_id": entity_id},
        )
    assert menuai.states.get(entity_id).state == old_value

    # Turning switch to OFF
    old_value = "on"
    menuai.states.async_set(entity_id, old_value)
    assert menuai.states.get(entity_id).state == old_value

    # Test
    with pytest.raises(expected, match=exc_translation):
        await menuai.services.async_call(
            "switch",
            "turn_off",
            blocking=True,
            target={"entity_id": entity_id},
        )
    assert menuai.states.get(entity_id).state == old_value
