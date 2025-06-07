"""Test Subaru component setup and updates."""

from unittest.mock import patch

from subarulink import InvalidCredentials, SubaruException

from menuai.components.menuai import (
    DOMAIN as HA_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from menuai.components.subaru.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.setup import async_setup_component

from .api_responses import (
    TEST_VIN_1_G1,
    TEST_VIN_2_EV,
    TEST_VIN_3_G3,
    VEHICLE_DATA,
    VEHICLE_STATUS_EV,
    VEHICLE_STATUS_G3,
)
from .conftest import (
    MOCK_API_FETCH,
    MOCK_API_UPDATE,
    TEST_ENTITY_ID,
    setup_subaru_config_entry,
)


async def test_setup_with_no_config(menuai: menuai) -> None:
    """Test DOMAIN is empty if there is no config."""
    assert await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()
    assert DOMAIN not in menuai.config_entries.async_domains()


async def test_setup_ev(menuai: menuai, ev_entry) -> None:
    """Test setup with an EV vehicle."""
    check_entry = menuai.config_entries.async_get_entry(ev_entry.entry_id)
    assert check_entry
    assert check_entry.state is ConfigEntryState.LOADED


async def test_setup_g3(menuai: menuai, subaru_config_entry) -> None:
    """Test setup with a G3 vehicle ."""
    await setup_subaru_config_entry(
        menuai,
        subaru_config_entry,
        vehicle_list=[TEST_VIN_3_G3],
        vehicle_data=VEHICLE_DATA[TEST_VIN_3_G3],
        vehicle_status=VEHICLE_STATUS_G3,
    )
    check_entry = menuai.config_entries.async_get_entry(subaru_config_entry.entry_id)
    assert check_entry
    assert check_entry.state is ConfigEntryState.LOADED


async def test_setup_g1(menuai: menuai, subaru_config_entry) -> None:
    """Test setup with a G1 vehicle."""
    await setup_subaru_config_entry(
        menuai,
        subaru_config_entry,
        vehicle_list=[TEST_VIN_1_G1],
        vehicle_data=VEHICLE_DATA[TEST_VIN_1_G1],
    )
    check_entry = menuai.config_entries.async_get_entry(subaru_config_entry.entry_id)
    assert check_entry
    assert check_entry.state is ConfigEntryState.LOADED


async def test_unsuccessful_connect(menuai: menuai, subaru_config_entry) -> None:
    """Test unsuccessful connect due to connectivity."""
    await setup_subaru_config_entry(
        menuai,
        subaru_config_entry,
        connect_effect=SubaruException("Service Unavailable"),
        vehicle_list=[TEST_VIN_2_EV],
        vehicle_data=VEHICLE_DATA[TEST_VIN_2_EV],
        vehicle_status=VEHICLE_STATUS_EV,
    )
    check_entry = menuai.config_entries.async_get_entry(subaru_config_entry.entry_id)
    assert check_entry
    assert check_entry.state is ConfigEntryState.SETUP_RETRY


async def test_invalid_credentials(menuai: menuai, subaru_config_entry) -> None:
    """Test invalid credentials."""
    await setup_subaru_config_entry(
        menuai,
        subaru_config_entry,
        connect_effect=InvalidCredentials("Invalid Credentials"),
        vehicle_list=[TEST_VIN_2_EV],
        vehicle_data=VEHICLE_DATA[TEST_VIN_2_EV],
        vehicle_status=VEHICLE_STATUS_EV,
    )
    check_entry = menuai.config_entries.async_get_entry(subaru_config_entry.entry_id)
    assert check_entry
    assert check_entry.state is ConfigEntryState.SETUP_ERROR


async def test_update_skip_unsubscribed(
    menuai: menuai, subaru_config_entry
) -> None:
    """Test update function skips vehicles without subscription."""
    await setup_subaru_config_entry(
        menuai,
        subaru_config_entry,
        vehicle_list=[TEST_VIN_1_G1],
        vehicle_data=VEHICLE_DATA[TEST_VIN_1_G1],
    )

    with patch(MOCK_API_FETCH) as mock_fetch:
        await menuai.services.async_call(
            HA_DOMAIN,
            SERVICE_UPDATE_ENTITY,
            {ATTR_ENTITY_ID: TEST_ENTITY_ID},
            blocking=True,
        )

        await menuai.async_block_till_done()
        mock_fetch.assert_not_called()


async def test_update_disabled(menuai: menuai, ev_entry) -> None:
    """Test update function disable option."""
    with (
        patch(
            MOCK_API_FETCH,
            side_effect=SubaruException("403 Error"),
        ),
        patch(
            MOCK_API_UPDATE,
        ) as mock_update,
    ):
        await menuai.services.async_call(
            HA_DOMAIN,
            SERVICE_UPDATE_ENTITY,
            {ATTR_ENTITY_ID: TEST_ENTITY_ID},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_update.assert_not_called()


async def test_fetch_failed(menuai: menuai, subaru_config_entry) -> None:
    """Tests when fetch fails."""
    await setup_subaru_config_entry(
        menuai,
        subaru_config_entry,
        vehicle_list=[TEST_VIN_2_EV],
        vehicle_data=VEHICLE_DATA[TEST_VIN_2_EV],
        vehicle_status=VEHICLE_STATUS_EV,
        fetch_effect=SubaruException("403 Error"),
    )

    test_entity = menuai.states.get(TEST_ENTITY_ID)
    assert test_entity.state == "unavailable"


async def test_unload_entry(menuai: menuai, ev_entry) -> None:
    """Test that entry is unloaded."""
    assert ev_entry.state is ConfigEntryState.LOADED
    assert await menuai.config_entries.async_unload(ev_entry.entry_id)
    await menuai.async_block_till_done()
    assert ev_entry.state is ConfigEntryState.NOT_LOADED
