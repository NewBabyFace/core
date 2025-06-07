"""Test BMW numbers."""

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
    """Test number options and values."""

    # Setup component
    with patch(
        "menuai.components.bmw_connected_drive.PLATFORMS",
        [Platform.NUMBER],
    ):
        mock_config_entry = await setup_mocked_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "new_value", "old_value", "remote_service"),
    [
        ("number.i4_edrive40_target_soc", "80", "100", "charging-settings"),
    ],
)
async def test_service_call_success(
    menuai: menuai,
    entity_id: str,
    new_value: str,
    old_value: str,
    remote_service: str,
    bmw_fixture: respx.Router,
) -> None:
    """Test successful number change."""

    # Setup component
    assert await setup_mocked_integration(menuai)
    menuai.states.async_set(entity_id, old_value)
    assert menuai.states.get(entity_id).state == old_value

    # Test
    await menuai.services.async_call(
        "number",
        "set_value",
        service_data={"value": new_value},
        blocking=True,
        target={"entity_id": entity_id},
    )
    check_remote_service_call(bmw_fixture, remote_service)
    assert menuai.states.get(entity_id).state == new_value


@pytest.mark.usefixtures("bmw_fixture")
@pytest.mark.parametrize(
    ("entity_id", "value"),
    [
        ("number.i4_edrive40_target_soc", "81"),
    ],
)
async def test_service_call_invalid_input(
    menuai: menuai,
    entity_id: str,
    value: str,
) -> None:
    """Test not allowed values for number inputs."""

    # Setup component
    assert await setup_mocked_integration(menuai)
    old_value = menuai.states.get(entity_id).state

    # Test
    with pytest.raises(
        ValueError,
        match="Target SoC must be an integer between 20 and 100 that is a multiple of 5.",
    ):
        await menuai.services.async_call(
            "number",
            "set_value",
            service_data={"value": value},
            blocking=True,
            target={"entity_id": entity_id},
        )
    assert menuai.states.get(entity_id).state == old_value


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
        (
            ValueError(
                "Target SoC must be an integer between 20 and 100 that is a multiple of 5."
            ),
            ValueError,
            "Target SoC must be an integer between 20 and 100 that is a multiple of 5.",
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
    entity_id = "number.i4_edrive40_target_soc"
    old_value = menuai.states.get(entity_id).state

    # Setup exception
    monkeypatch.setattr(
        RemoteServices,
        "trigger_remote_service",
        AsyncMock(side_effect=raised),
    )

    # Test
    with pytest.raises(expected, match=exc_translation):
        await menuai.services.async_call(
            "number",
            "set_value",
            service_data={"value": "80"},
            blocking=True,
            target={"entity_id": entity_id},
        )
    assert menuai.states.get(entity_id).state == old_value
