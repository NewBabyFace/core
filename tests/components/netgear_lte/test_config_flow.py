"""Test Netgear LTE config flow."""

from unittest.mock import patch

from menuai.components.netgear_lte.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_SOURCE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import CONF_DATA


def _patch_setup():
    return patch(
        "menuai.components.netgear_lte.async_setup_entry", return_value=True
    )


async def test_flow_user_form(menuai: menuai, connection: None) -> None:
    """Test that the user set up form is served."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with _patch_setup():
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CONF_DATA,
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Netgear LM1200"
    assert result["data"] == CONF_DATA
    assert result["context"]["unique_id"] == "FFFFFFFFFFFFF"


async def test_flow_already_configured(
    menuai: menuai, setup_integration: None
) -> None:
    """Test config flow aborts when already configured."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=CONF_DATA,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_flow_user_cannot_connect(
    menuai: menuai, cannot_connect: None
) -> None:
    """Test connection error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=CONF_DATA,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "cannot_connect"


async def test_flow_user_unknown_error(menuai: menuai, unknown: None) -> None:
    """Test unknown error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=CONF_DATA,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "unknown"
