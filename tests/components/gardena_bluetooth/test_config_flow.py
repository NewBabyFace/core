"""Test the Gardena Bluetooth config flow."""

from unittest.mock import Mock

from gardena_bluetooth.exceptions import CharacteristicNotFound
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai import config_entries
from menuai.components.gardena_bluetooth.const import DOMAIN
from menuai.core import menuai

from . import (
    MISSING_MANUFACTURER_DATA_SERVICE_INFO,
    MISSING_SERVICE_SERVICE_INFO,
    UNSUPPORTED_GROUP_SERVICE_INFO,
    WATER_TIMER_SERVICE_INFO,
    WATER_TIMER_UNNAMED_SERVICE_INFO,
)

from tests.components.bluetooth import inject_bluetooth_service_info

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_user_selection(
    menuai: menuai,
    snapshot: SnapshotAssertion,
) -> None:
    """Test we can select a device."""

    inject_bluetooth_service_info(menuai, WATER_TIMER_SERVICE_INFO)
    inject_bluetooth_service_info(menuai, WATER_TIMER_UNNAMED_SERVICE_INFO)
    await menuai.async_block_till_done(wait_background_tasks=True)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result == snapshot

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"address": "00000000-0000-0000-0000-000000000001"},
    )
    assert result == snapshot

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result == snapshot


async def test_failed_connect(
    menuai: menuai,
    mock_client: Mock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test we can select a device."""

    inject_bluetooth_service_info(menuai, WATER_TIMER_SERVICE_INFO)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result == snapshot

    mock_client.read_char.side_effect = CharacteristicNotFound("something went wrong")

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"address": "00000000-0000-0000-0000-000000000001"},
    )
    assert result == snapshot

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result == snapshot


async def test_no_devices(
    menuai: menuai,
    snapshot: SnapshotAssertion,
) -> None:
    """Test missing device."""

    inject_bluetooth_service_info(menuai, MISSING_MANUFACTURER_DATA_SERVICE_INFO)
    inject_bluetooth_service_info(menuai, MISSING_SERVICE_SERVICE_INFO)
    inject_bluetooth_service_info(menuai, UNSUPPORTED_GROUP_SERVICE_INFO)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result == snapshot


async def test_bluetooth(
    menuai: menuai,
    snapshot: SnapshotAssertion,
) -> None:
    """Test bluetooth device discovery."""

    # Inject the service info will trigger the flow to start
    inject_bluetooth_service_info(menuai, WATER_TIMER_SERVICE_INFO)
    await menuai.async_block_till_done(wait_background_tasks=True)

    result = next(iter(menuai.config_entries.flow.async_progress_by_handler(DOMAIN)))

    assert result == snapshot

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result == snapshot


async def test_bluetooth_invalid(
    menuai: menuai,
    snapshot: SnapshotAssertion,
) -> None:
    """Test bluetooth device discovery with invalid data."""

    inject_bluetooth_service_info(menuai, UNSUPPORTED_GROUP_SERVICE_INFO)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=UNSUPPORTED_GROUP_SERVICE_INFO,
    )
    assert result == snapshot
