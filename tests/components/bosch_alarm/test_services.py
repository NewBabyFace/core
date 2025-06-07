"""Tests for Bosch Alarm component."""

import asyncio
from collections.abc import AsyncGenerator
import datetime as dt
from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol

from menuai.components.bosch_alarm.const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DATETIME,
    DOMAIN,
    SERVICE_SET_DATE_TIME,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from . import setup_integration

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
async def platforms() -> AsyncGenerator[None]:
    """Return the platforms to be loaded for this test."""
    with patch("menuai.components.bosch_alarm.PLATFORMS", []):
        yield


async def test_set_date_time_service(
    menuai: menuai,
    mock_panel: AsyncMock,
    area: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the service calls succeed if the service call is valid."""
    await setup_integration(menuai, mock_config_entry)
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SET_DATE_TIME,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_DATETIME: dt_util.now(),
        },
        blocking=True,
    )
    mock_panel.set_panel_date.assert_called_once()


async def test_set_date_time_service_fails_bad_entity(
    menuai: menuai,
    mock_panel: AsyncMock,
    area: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the service calls fail if the service call is done for an incorrect entity."""
    await setup_integration(menuai, mock_config_entry)
    with pytest.raises(
        ServiceValidationError,
        match='Integration "bad-config_id" not found in registry',
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SET_DATE_TIME,
            {
                ATTR_CONFIG_ENTRY_ID: "bad-config_id",
                ATTR_DATETIME: dt_util.now(),
            },
            blocking=True,
        )


async def test_set_date_time_service_fails_bad_params(
    menuai: menuai,
    mock_panel: AsyncMock,
    area: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the service calls fail if the service call is done with incorrect params."""
    await setup_integration(menuai, mock_config_entry)
    with pytest.raises(
        vol.MultipleInvalid,
        match=r"Invalid datetime specified:  for dictionary value @ data\['datetime'\]",
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SET_DATE_TIME,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                ATTR_DATETIME: "",
            },
            blocking=True,
        )


async def test_set_date_time_service_fails_bad_year_before(
    menuai: menuai,
    mock_panel: AsyncMock,
    area: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the service calls fail if the panel fails the service call."""
    await setup_integration(menuai, mock_config_entry)
    with pytest.raises(
        vol.MultipleInvalid,
        match=r"datetime must be before 2038 for dictionary value @ data\['datetime'\]",
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SET_DATE_TIME,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                ATTR_DATETIME: dt.datetime(2038, 1, 1),
            },
            blocking=True,
        )


async def test_set_date_time_service_fails_bad_year_after(
    menuai: menuai,
    mock_panel: AsyncMock,
    area: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the service calls fail if the panel fails the service call."""
    await setup_integration(menuai, mock_config_entry)
    mock_panel.set_panel_date.side_effect = ValueError()
    with pytest.raises(
        vol.MultipleInvalid,
        match=r"datetime must be after 2009 for dictionary value @ data\['datetime'\]",
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SET_DATE_TIME,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                ATTR_DATETIME: dt.datetime(2009, 1, 1),
            },
            blocking=True,
        )


async def test_set_date_time_service_fails_connection_error(
    menuai: menuai,
    mock_panel: AsyncMock,
    area: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the service calls fail if the panel fails the service call."""
    await setup_integration(menuai, mock_config_entry)
    mock_panel.set_panel_date.side_effect = asyncio.InvalidStateError()
    with pytest.raises(
        menuaiError,
        match=f'Could not connect to "{mock_config_entry.title}"',
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SET_DATE_TIME,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                ATTR_DATETIME: dt_util.now(),
            },
            blocking=True,
        )


async def test_set_date_time_service_fails_unloaded(
    menuai: menuai,
    mock_panel: AsyncMock,
    area: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the service calls fail if the config entry is unloaded."""
    await async_setup_component(menuai, DOMAIN, {})
    mock_config_entry.add_to_menuai(menuai)
    with pytest.raises(
        menuaiError,
        match=f"{mock_config_entry.title} is not loaded",
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SET_DATE_TIME,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                ATTR_DATETIME: dt_util.now(),
            },
            blocking=True,
        )
