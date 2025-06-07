"""Test iss config flow."""

from unittest.mock import patch

from menuai.components.iss.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_SHOW_ON_MAP
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_create_entry(menuai: menuai) -> None:
    """Test we can finish a config flow."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    with patch("menuai.components.iss.async_setup_entry", return_value=True):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

        assert result.get("type") is FlowResultType.CREATE_ENTRY
        assert result.get("result").data == {}


async def test_integration_already_exists(menuai: menuai) -> None:
    """Test we only allow a single config flow."""

    MockConfigEntry(
        domain=DOMAIN,
        data={},
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={}
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "single_instance_allowed"


async def test_options(menuai: menuai) -> None:
    """Test options flow."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
    )

    config_entry.add_to_menuai(menuai)

    with patch("menuai.components.iss.async_setup_entry", return_value=True):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)

        optionflow = await menuai.config_entries.options.async_init(config_entry.entry_id)

        configured = await menuai.config_entries.options.async_configure(
            optionflow["flow_id"],
            user_input={
                CONF_SHOW_ON_MAP: True,
            },
        )

        assert configured.get("type") is FlowResultType.CREATE_ENTRY
        assert config_entry.options == {CONF_SHOW_ON_MAP: True}
