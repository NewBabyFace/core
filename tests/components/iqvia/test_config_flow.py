"""Define tests for the IQVIA config flow."""

from typing import Any

import pytest

from menuai.components.iqvia.const import CONF_ZIP_CODE, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


@pytest.mark.usefixtures("config_entry")
async def test_duplicate_error(menuai: menuai, config: dict[str, Any]) -> None:
    """Test that errors are shown when duplicates are added."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=config
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_invalid_zip_code(menuai: menuai) -> None:
    """Test that an invalid ZIP code key throws an error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={CONF_ZIP_CODE: "bad"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ZIP_CODE: "invalid_zip_code"}


async def test_show_form(menuai: menuai) -> None:
    """Test that the form is served with no input."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.usefixtures("setup_iqvia")
async def test_step_user(menuai: menuai, config: dict[str, Any]) -> None:
    """Test that the user step works (without MFA)."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=config
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "12345"
    assert result["data"] == {CONF_ZIP_CODE: "12345"}
