"""Test Prusalink buttons."""

from unittest.mock import patch

from pyprusalink.types import Conflict
import pytest

from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.setup import async_setup_component

from tests.typing import ClientSessionGenerator


@pytest.fixture(autouse=True)
def setup_button_platform_only():
    """Only setup button platform."""
    with patch("menuai.components.prusalink.PLATFORMS", [Platform.BUTTON]):
        yield


@pytest.mark.parametrize(
    ("object_id", "method"),
    [
        ("mock_title_cancel_job", "cancel_job"),
        ("mock_title_pause_job", "pause_job"),
    ],
)
async def test_button_pause_cancel(
    menuai: menuai,
    mock_config_entry,
    mock_api,
    menuai_client: ClientSessionGenerator,
    mock_job_api_printing,
    mock_get_status_printing,
    object_id,
    method,
) -> None:
    """Test cancel and pause button."""
    entity_id = f"button.{object_id}"
    assert await async_setup_component(menuai, "prusalink", {})
    state = menuai.states.get(entity_id)
    assert state is not None
    assert state.state == "unknown"

    with patch(f"pyprusalink.PrusaLink.{method}") as mock_meth:
        await menuai.services.async_call(
            "button",
            "press",
            {"entity_id": entity_id},
            blocking=True,
        )

    assert len(mock_meth.mock_calls) == 1

    # Verify it calls correct method + does error handling
    with (
        pytest.raises(menuaiError),
        patch(f"pyprusalink.PrusaLink.{method}", side_effect=Conflict),
    ):
        await menuai.services.async_call(
            "button",
            "press",
            {"entity_id": entity_id},
            blocking=True,
        )


@pytest.mark.parametrize(
    ("object_id", "method"),
    [
        ("mock_title_cancel_job", "cancel_job"),
        ("mock_title_resume_job", "resume_job"),
    ],
)
async def test_button_resume_cancel(
    menuai: menuai,
    mock_config_entry,
    mock_api,
    menuai_client: ClientSessionGenerator,
    mock_job_api_paused,
    object_id,
    method,
) -> None:
    """Test resume button."""
    entity_id = f"button.{object_id}"
    assert await async_setup_component(menuai, "prusalink", {})
    state = menuai.states.get(entity_id)
    assert state is not None
    assert state.state == "unknown"

    with (
        patch(f"pyprusalink.PrusaLink.{method}") as mock_meth,
        patch(
            "menuai.components.prusalink.coordinator.PrusaLinkUpdateCoordinator._fetch_data"
        ),
    ):
        await menuai.services.async_call(
            "button",
            "press",
            {"entity_id": entity_id},
            blocking=True,
        )

    assert len(mock_meth.mock_calls) == 1

    # Verify it calls correct method + does error handling
    with (
        pytest.raises(menuaiError),
        patch(f"pyprusalink.PrusaLink.{method}", side_effect=Conflict),
    ):
        await menuai.services.async_call(
            "button",
            "press",
            {"entity_id": entity_id},
            blocking=True,
        )
