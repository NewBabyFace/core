"""Test the Canary config flow."""

from unittest.mock import patch

from requests import ConnectTimeout, HTTPError

from menuai.components.canary.const import (
    CONF_FFMPEG_ARGUMENTS,
    DEFAULT_FFMPEG_ARGUMENTS,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_TIMEOUT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import USER_INPUT, _patch_async_setup_entry, init_integration


async def test_user_form(menuai: menuai, canary_config_flow) -> None:
    """Test we get the user initiated form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with _patch_async_setup_entry() as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test-username"
    assert result["data"] == {**USER_INPUT, CONF_TIMEOUT: DEFAULT_TIMEOUT}

    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_form_cannot_connect(
    menuai: menuai, canary_config_flow
) -> None:
    """Test we handle errors that should trigger the cannot connect error."""
    canary_config_flow.side_effect = HTTPError()

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    canary_config_flow.side_effect = ConnectTimeout()

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_form_unexpected_exception(
    menuai: menuai, canary_config_flow
) -> None:
    """Test we handle unexpected exception."""
    canary_config_flow.side_effect = Exception()

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"


async def test_user_form_single_instance_allowed(
    menuai: menuai, canary_config_flow
) -> None:
    """Test that configuring more than one instance is rejected."""
    await init_integration(menuai, skip_entry_setup=True)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=USER_INPUT,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow(menuai: menuai, canary) -> None:
    """Test updating options."""
    with patch("menuai.components.canary.PLATFORMS", []):
        entry = await init_integration(menuai)

    assert entry.options[CONF_FFMPEG_ARGUMENTS] == DEFAULT_FFMPEG_ARGUMENTS
    assert entry.options[CONF_TIMEOUT] == DEFAULT_TIMEOUT

    result = await menuai.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    with _patch_async_setup_entry():
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_FFMPEG_ARGUMENTS: "-v", CONF_TIMEOUT: 7},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_FFMPEG_ARGUMENTS] == "-v"
    assert result["data"][CONF_TIMEOUT] == 7
