"""Test VoIP config flow."""

from unittest.mock import patch

from menuai import config_entries
from menuai.components import voip
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form_user(menuai: menuai) -> None:
    """Test user form config flow."""

    result = await menuai.config_entries.flow.async_init(
        voip.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    with patch(
        "menuai.components.voip.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_single_instance(
    menuai: menuai, config_entry: config_entries.ConfigEntry
) -> None:
    """Test that only one instance can be created."""
    result = await menuai.config_entries.flow.async_init(
        voip.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow(menuai: menuai) -> None:
    """Test config flow options."""
    config_entry = MockConfigEntry(
        domain=voip.DOMAIN,
        data={},
        unique_id="1234",
    )
    config_entry.add_to_menuai(menuai)

    assert config_entry.options == {}

    result = await menuai.config_entries.options.async_init(
        config_entry.entry_id,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    # Default
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {"sip_port": 5060}

    # Manual
    result = await menuai.config_entries.options.async_init(
        config_entry.entry_id,
    )
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"sip_port": 5061},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {"sip_port": 5061}

    # Manual with user
    result = await menuai.config_entries.options.async_init(
        config_entry.entry_id,
    )
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"sip_port": 5061, "sip_user": "HA"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {"sip_port": 5061, "sip_user": "HA"}

    # Manual remove user
    result = await menuai.config_entries.options.async_init(
        config_entry.entry_id,
    )

    assert config_entry.options == {"sip_port": 5061, "sip_user": "HA"}

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"sip_port": 5060, "sip_user": ""},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {"sip_port": 5060}
