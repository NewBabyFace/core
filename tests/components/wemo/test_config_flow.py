"""Tests for Wemo config flow."""

from dataclasses import asdict

from menuai.components.wemo.const import DOMAIN
from menuai.components.wemo.coordinator import Options
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry, patch


async def test_not_discovered(menuai: menuai) -> None:
    """Test setting up with no devices discovered."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    with patch("menuai.components.wemo.config_flow.pywemo") as mock_pywemo:
        mock_pywemo.discover_devices.return_value = []
        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_options(menuai: menuai) -> None:
    """Test updating options."""
    options = Options(enable_subscription=False, enable_long_press=False)
    entry = MockConfigEntry(domain=DOMAIN, title="Wemo")
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input=asdict(options)
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert Options(**result["data"]) == options


async def test_invalid_options(menuai: menuai) -> None:
    """Test invalid option combinations."""
    entry = MockConfigEntry(domain=DOMAIN, title="Wemo")
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    # enable_subscription must be True if enable_long_press is True (default).
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input={"enable_subscription": False}
    )
    assert result["errors"] == {
        "enable_subscription": "long_press_requires_subscription"
    }
