"""Test Utility Meter diagnostics."""

from aiohttp.test_utils import TestClient
from freezegun import freeze_time
import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.auth.models import Credentials
from menuai.components.utility_meter.const import DOMAIN
from menuai.components.utility_meter.sensor import ATTR_LAST_RESET
from menuai.core import menuai, State

from tests.common import (
    CLIENT_ID,
    MockConfigEntry,
    MockUser,
    mock_restore_cache_with_extra_data,
)
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def generate_new_menuai_access_token(
    menuai: menuai, menuai_admin_user: MockUser, menuai_admin_credential: Credentials
) -> str:
    """Return an access token to access MenuAI."""
    await menuai.auth.async_link_user(menuai_admin_user, menuai_admin_credential)

    refresh_token = await menuai.auth.async_create_refresh_token(
        menuai_admin_user, CLIENT_ID, credential=menuai_admin_credential
    )
    return menuai.auth.async_create_access_token(refresh_token)


def _get_test_client_generator(
    menuai: menuai, aiohttp_client: ClientSessionGenerator, new_token: str
):
    """Return a test client generator.""."""

    async def auth_client() -> TestClient:
        return await aiohttp_client(
            menuai.http.app, headers={"Authorization": f"Bearer {new_token}"}
        )

    return auth_client


@freeze_time("2024-04-06 00:00:00+00:00")
@pytest.mark.usefixtures("socket_enabled")
async def test_diagnostics(
    menuai: menuai,
    aiohttp_client: ClientSessionGenerator,
    menuai_admin_user: MockUser,
    menuai_admin_credential: Credentials,
    snapshot: SnapshotAssertion,
) -> None:
    """Test generating diagnostics for a config entry."""

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "cycle": "monthly",
            "delta_values": False,
            "name": "Energy Bill",
            "net_consumption": False,
            "offset": 0,
            "periodically_resetting": True,
            "source": "sensor.input1",
            "tariffs": [
                "tariff0",
                "tariff1",
            ],
        },
        title="Energy Bill",
    )

    last_reset = "2024-04-05T00:00:00+00:00"

    # Set up the sensors restore data
    mock_restore_cache_with_extra_data(
        menuai,
        [
            (
                State(
                    "sensor.energy_bill_tariff0",
                    "3",
                    attributes={
                        ATTR_LAST_RESET: last_reset,
                    },
                ),
                {
                    "native_value": {
                        "__type": "<class 'decimal.Decimal'>",
                        "decimal_str": "3",
                    },
                    "native_unit_of_measurement": "kWh",
                    "last_reset": last_reset,
                    "last_period": "0",
                    "last_valid_state": 3,
                    "status": "collecting",
                },
            ),
            (
                State(
                    "sensor.energy_bill_tariff1",
                    "7",
                    attributes={
                        ATTR_LAST_RESET: last_reset,
                    },
                ),
                {
                    "native_value": {
                        "__type": "<class 'decimal.Decimal'>",
                        "decimal_str": "7",
                    },
                    "native_unit_of_measurement": "kWh",
                    "last_reset": last_reset,
                    "last_period": "0",
                    "last_valid_state": 7,
                    "status": "paused",
                },
            ),
        ],
    )

    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    # Since we are freezing time only when we enter this test, we need to
    # manually create a new token and clients since the token created by
    # the fixtures would not be valid.
    new_token = await generate_new_menuai_access_token(
        menuai, menuai_admin_user, menuai_admin_credential
    )

    diag = await get_diagnostics_for_config_entry(
        menuai, _get_test_client_generator(menuai, aiohttp_client, new_token), config_entry
    )

    assert diag == snapshot(exclude=props("entry_id", "created_at", "modified_at"))
