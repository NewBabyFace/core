"""Test the Leaone config flow."""

from unittest.mock import patch

from menuai import config_entries
from menuai.components.leaone.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import SCALE_SERVICE_INFO

from tests.common import MockConfigEntry


async def test_async_step_user_no_devices_found(menuai: menuai) -> None:
    """Test setup from service info cache with no devices found."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_async_step_user_with_found_devices(menuai: menuai) -> None:
    """Test setup from service info cache with devices found."""
    with patch(
        "menuai.components.leaone.config_flow.async_discovered_service_info",
        return_value=[SCALE_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    with patch("menuai.components.leaone.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": "5F:5A:5C:52:D3:94"},
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "TZC4 D394"
    assert result2["data"] == {}
    assert result2["result"].unique_id == "5F:5A:5C:52:D3:94"


async def test_async_step_user_device_added_between_steps(menuai: menuai) -> None:
    """Test the device gets added via another flow between steps."""
    with patch(
        "menuai.components.leaone.config_flow.async_discovered_service_info",
        return_value=[SCALE_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="5F:5A:5C:52:D3:94",
    )
    entry.add_to_menuai(menuai)

    with patch("menuai.components.leaone.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"address": "5F:5A:5C:52:D3:94"},
        )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_async_step_user_with_found_devices_already_setup(
    menuai: menuai,
) -> None:
    """Test setup from service info cache with devices found."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="5F:5A:5C:52:D3:94",
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.leaone.config_flow.async_discovered_service_info",
        return_value=[SCALE_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"
