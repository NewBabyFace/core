"""Test services in Nord Pool."""

from unittest.mock import patch

from pynordpool import (
    NordPoolAuthenticationError,
    NordPoolEmptyResponseError,
    NordPoolError,
)
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.nordpool.const import DOMAIN
from menuai.components.nordpool.services import (
    ATTR_AREAS,
    ATTR_CONFIG_ENTRY,
    ATTR_CURRENCY,
    SERVICE_GET_PRICES_FOR_DATE,
)
from menuai.const import ATTR_DATE
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError

from tests.common import MockConfigEntry

TEST_SERVICE_DATA = {
    ATTR_CONFIG_ENTRY: "to_replace",
    ATTR_DATE: "2024-11-05",
    ATTR_AREAS: "SE3",
    ATTR_CURRENCY: "EUR",
}
TEST_SERVICE_DATA_USE_DEFAULTS = {
    ATTR_CONFIG_ENTRY: "to_replace",
    ATTR_DATE: "2024-11-05",
}


@pytest.mark.freeze_time("2024-11-05T18:00:00+00:00")
async def test_service_call(
    menuai: menuai,
    load_int: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test get_prices_for_date service call."""

    service_data = TEST_SERVICE_DATA.copy()
    service_data[ATTR_CONFIG_ENTRY] = load_int.entry_id
    response = await menuai.services.async_call(
        DOMAIN,
        SERVICE_GET_PRICES_FOR_DATE,
        service_data,
        blocking=True,
        return_response=True,
    )

    assert response == snapshot
    price_value = response["SE3"][0]["price"]

    service_data = TEST_SERVICE_DATA_USE_DEFAULTS.copy()
    service_data[ATTR_CONFIG_ENTRY] = load_int.entry_id
    response = await menuai.services.async_call(
        DOMAIN,
        SERVICE_GET_PRICES_FOR_DATE,
        service_data,
        blocking=True,
        return_response=True,
    )

    assert "SE3" in response
    assert response["SE3"][0]["price"] == price_value


@pytest.mark.parametrize(
    ("error", "key"),
    [
        (NordPoolAuthenticationError, "authentication_error"),
        (NordPoolError, "connection_error"),
    ],
)
@pytest.mark.freeze_time("2024-11-05T18:00:00+00:00")
async def test_service_call_failures(
    menuai: menuai,
    load_int: MockConfigEntry,
    error: Exception,
    key: str,
) -> None:
    """Test get_prices_for_date service call when it fails."""
    service_data = TEST_SERVICE_DATA.copy()
    service_data[ATTR_CONFIG_ENTRY] = load_int.entry_id

    with (
        patch(
            "menuai.components.nordpool.coordinator.NordPoolClient.async_get_delivery_period",
            side_effect=error,
        ),
        pytest.raises(ServiceValidationError) as err,
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_GET_PRICES_FOR_DATE,
            service_data,
            blocking=True,
            return_response=True,
        )
    assert err.value.translation_key == key


@pytest.mark.freeze_time("2024-11-05T18:00:00+00:00")
async def test_empty_response_returns_empty_list(
    menuai: menuai,
    load_int: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test get_prices_for_date service call return empty list for empty response."""
    service_data = TEST_SERVICE_DATA.copy()
    service_data[ATTR_CONFIG_ENTRY] = load_int.entry_id

    with (
        patch(
            "menuai.components.nordpool.coordinator.NordPoolClient.async_get_delivery_period",
            side_effect=NordPoolEmptyResponseError,
        ),
    ):
        response = await menuai.services.async_call(
            DOMAIN,
            SERVICE_GET_PRICES_FOR_DATE,
            service_data,
            blocking=True,
            return_response=True,
        )

    assert response == snapshot


@pytest.mark.freeze_time("2024-11-05T18:00:00+00:00")
async def test_service_call_config_entry_bad_state(
    menuai: menuai,
    load_int: MockConfigEntry,
) -> None:
    """Test get_prices_for_date service call when config entry bad state."""

    with pytest.raises(ServiceValidationError) as err:
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_GET_PRICES_FOR_DATE,
            TEST_SERVICE_DATA,
            blocking=True,
            return_response=True,
        )
    assert err.value.translation_key == "entry_not_found"

    service_data = TEST_SERVICE_DATA.copy()
    service_data[ATTR_CONFIG_ENTRY] = load_int.entry_id
    await menuai.config_entries.async_unload(load_int.entry_id)
    await menuai.async_block_till_done()

    with pytest.raises(ServiceValidationError) as err:
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_GET_PRICES_FOR_DATE,
            service_data,
            blocking=True,
            return_response=True,
        )
    assert err.value.translation_key == "entry_not_loaded"
