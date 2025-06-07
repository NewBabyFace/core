"""Test the Raspberry Pi config flow."""

from unittest.mock import patch

from menuai.components.raspberry_pi.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry, MockModule, mock_integration


async def test_config_flow(menuai: menuai) -> None:
    """Test the config flow."""
    mock_integration(menuai, MockModule("menuaiio"))

    with patch(
        "menuai.components.raspberry_pi.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": "system"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Raspberry Pi"
    assert result["data"] == {}
    assert result["options"] == {}
    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options == {}
    assert config_entry.title == "Raspberry Pi"


async def test_config_flow_single_entry(menuai: menuai) -> None:
    """Test only a single entry is allowed."""
    mock_integration(menuai, MockModule("menuaiio"))

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
        title="Raspberry Pi",
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.raspberry_pi.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": "system"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
    mock_setup_entry.assert_not_called()
