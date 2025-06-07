"""Tests for the Slide Local button platform."""

from unittest.mock import AsyncMock

from goslideapi.goslideapi import (
    AuthenticationFailed,
    ClientConnectionError,
    ClientTimeoutError,
    DigestAuthCalcError,
)
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import setup_platform

from tests.common import MockConfigEntry, snapshot_platform


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_slide_api: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    await setup_platform(menuai, mock_config_entry, [Platform.BUTTON])

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_pressing_button(
    menuai: menuai,
    mock_slide_api: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test pressing button."""
    await setup_platform(menuai, mock_config_entry, [Platform.BUTTON])

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {
            ATTR_ENTITY_ID: "button.slide_bedroom_calibrate",
        },
        blocking=True,
    )
    mock_slide_api.slide_calibrate.assert_called_once()


@pytest.mark.parametrize(
    ("exception"),
    [
        ClientConnectionError,
        ClientTimeoutError,
        AuthenticationFailed,
        DigestAuthCalcError,
    ],
)
async def test_pressing_button_exception(
    menuai: menuai,
    exception: Exception,
    mock_slide_api: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test pressing button."""
    await setup_platform(menuai, mock_config_entry, [Platform.BUTTON])

    mock_slide_api.slide_calibrate.side_effect = exception

    with pytest.raises(
        menuaiError,
        match="Error while sending the calibration request to the device",
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: "button.slide_bedroom_calibrate",
            },
            blocking=True,
        )
