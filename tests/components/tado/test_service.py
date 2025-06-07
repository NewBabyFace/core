"""The serive tests for the tado platform."""

import json
from unittest.mock import patch

import pytest
from requests.exceptions import RequestException

from menuai.components.tado.const import (
    CONF_CONFIG_ENTRY,
    CONF_READING,
    DOMAIN,
    SERVICE_ADD_METER_READING,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError

from .util import async_init_integration

from tests.common import MockConfigEntry, async_load_fixture


async def test_has_services(
    menuai: menuai,
) -> None:
    """Test the existence of the Tado Service."""

    await async_init_integration(menuai)

    assert menuai.services.has_service(DOMAIN, SERVICE_ADD_METER_READING)


async def test_add_meter_readings(
    menuai: menuai,
) -> None:
    """Test the add_meter_readings service."""

    await async_init_integration(menuai)

    config_entry: MockConfigEntry = menuai.config_entries.async_entries(DOMAIN)[0]
    fixture: str = await async_load_fixture(menuai, "add_readings_success.json", DOMAIN)
    with patch(
        "PyTado.interface.api.Tado.set_eiq_meter_readings",
        return_value=json.loads(fixture),
    ):
        response: None = await menuai.services.async_call(
            DOMAIN,
            SERVICE_ADD_METER_READING,
            service_data={
                CONF_CONFIG_ENTRY: config_entry.entry_id,
                CONF_READING: 1234,
            },
            blocking=True,
        )
        assert response is None


async def test_add_meter_readings_exception(
    menuai: menuai,
) -> None:
    """Test the add_meter_readings service with a RequestException."""

    await async_init_integration(menuai)

    config_entry: MockConfigEntry = menuai.config_entries.async_entries(DOMAIN)[0]
    with (
        patch(
            "PyTado.interface.api.Tado.set_eiq_meter_readings",
            side_effect=RequestException("Error"),
        ),
        pytest.raises(menuaiError) as exc,
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_ADD_METER_READING,
            service_data={
                CONF_CONFIG_ENTRY: config_entry.entry_id,
                CONF_READING: 1234,
            },
            blocking=True,
        )

    assert "Error setting Tado meter reading: Error" in str(exc.value)


async def test_add_meter_readings_invalid(
    menuai: menuai,
) -> None:
    """Test the add_meter_readings service with an invalid_meter_reading response."""

    await async_init_integration(menuai)

    config_entry: MockConfigEntry = menuai.config_entries.async_entries(DOMAIN)[0]
    fixture: str = await async_load_fixture(
        menuai, "add_readings_invalid_meter_reading.json", DOMAIN
    )
    with (
        patch(
            "PyTado.interface.api.Tado.set_eiq_meter_readings",
            return_value=json.loads(fixture),
        ),
        pytest.raises(menuaiError) as exc,
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_ADD_METER_READING,
            service_data={
                CONF_CONFIG_ENTRY: config_entry.entry_id,
                CONF_READING: 1234,
            },
            blocking=True,
        )

    assert "invalid new reading" in str(exc)


async def test_add_meter_readings_duplicate(
    menuai: menuai,
) -> None:
    """Test the add_meter_readings service with a duplicated_meter_reading response."""

    await async_init_integration(menuai)

    config_entry: MockConfigEntry = menuai.config_entries.async_entries(DOMAIN)[0]
    fixture: str = await async_load_fixture(
        menuai, "add_readings_duplicated_meter_reading.json", DOMAIN
    )
    with (
        patch(
            "PyTado.interface.api.Tado.set_eiq_meter_readings",
            return_value=json.loads(fixture),
        ),
        pytest.raises(menuaiError) as exc,
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_ADD_METER_READING,
            service_data={
                CONF_CONFIG_ENTRY: config_entry.entry_id,
                CONF_READING: 1234,
            },
            blocking=True,
        )

    assert "reading already exists for date" in str(exc)
