"""Tests for the Hisense AEH-W4A1 init file."""

from unittest.mock import patch

from pyaehw4a1 import exceptions

from menuai import config_entries
from menuai.components import hisense_aehw4a1
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.setup import async_setup_component


async def test_creating_entry_sets_up_climate_discovery(menuai: menuai) -> None:
    """Test setting up Hisense AEH-W4A1 loads the climate component."""
    with (
        patch(
            "menuai.components.hisense_aehw4a1.config_flow.AehW4a1.discovery",
            return_value=["1.2.3.4"],
        ),
        patch(
            "menuai.components.hisense_aehw4a1.climate.async_setup_entry",
            return_value=True,
        ) as mock_setup,
    ):
        result = await menuai.config_entries.flow.async_init(
            hisense_aehw4a1.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Confirmation form
        assert result["type"] is FlowResultType.FORM

        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["type"] is FlowResultType.CREATE_ENTRY

        await menuai.async_block_till_done()

    assert len(mock_setup.mock_calls) == 1


async def test_configuring_hisense_w4a1_create_entry(menuai: menuai) -> None:
    """Test that specifying config will create an entry."""
    with (
        patch(
            "menuai.components.hisense_aehw4a1.config_flow.AehW4a1.check",
            return_value=True,
        ),
        patch(
            "menuai.components.hisense_aehw4a1.async_setup_entry",
            return_value=True,
        ) as mock_setup,
    ):
        await async_setup_component(
            menuai,
            hisense_aehw4a1.DOMAIN,
            {"hisense_aehw4a1": {"ip_address": ["1.2.3.4"]}},
        )
        await menuai.async_block_till_done()

    assert len(mock_setup.mock_calls) == 1


async def test_configuring_hisense_w4a1_not_creates_entry_for_device_not_found(
    menuai: menuai,
) -> None:
    """Test that specifying config will not create an entry."""
    with (
        patch(
            "menuai.components.hisense_aehw4a1.config_flow.AehW4a1.check",
            side_effect=exceptions.ConnectionError,
        ),
        patch(
            "menuai.components.hisense_aehw4a1.async_setup_entry",
            return_value=True,
        ) as mock_setup,
    ):
        await async_setup_component(
            menuai,
            hisense_aehw4a1.DOMAIN,
            {"hisense_aehw4a1": {"ip_address": ["1.2.3.4"]}},
        )
        await menuai.async_block_till_done()

    assert len(mock_setup.mock_calls) == 0


async def test_configuring_hisense_w4a1_not_creates_entry_for_empty_import(
    menuai: menuai,
) -> None:
    """Test that specifying config will not create an entry."""
    with patch(
        "menuai.components.hisense_aehw4a1.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        await async_setup_component(menuai, hisense_aehw4a1.DOMAIN, {})
        await menuai.async_block_till_done()

    assert len(mock_setup.mock_calls) == 0
