"""Test the Cloudflare config flow."""

from unittest.mock import MagicMock

import pycfdns

from menuai.components.cloudflare.const import CONF_RECORDS, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_API_TOKEN, CONF_SOURCE, CONF_ZONE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import (
    ENTRY_CONFIG,
    USER_INPUT,
    USER_INPUT_RECORDS,
    USER_INPUT_ZONE,
    patch_async_setup_entry,
)

from tests.common import MockConfigEntry


async def test_user_form(menuai: menuai, cfupdate_flow: MagicMock) -> None:
    """Test we get the user initiated form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zone"
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT_ZONE,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "records"
    assert result["errors"] is None

    with patch_async_setup_entry() as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT_RECORDS,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == USER_INPUT_ZONE[CONF_ZONE]

    assert result["data"]
    assert result["data"][CONF_API_TOKEN] == USER_INPUT[CONF_API_TOKEN]
    assert result["data"][CONF_ZONE] == USER_INPUT_ZONE[CONF_ZONE]
    assert result["data"][CONF_RECORDS] == USER_INPUT_RECORDS[CONF_RECORDS]

    assert result["result"]
    assert result["result"].unique_id == USER_INPUT_ZONE[CONF_ZONE]

    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_form_cannot_connect(
    menuai: menuai, cfupdate_flow: MagicMock
) -> None:
    """Test we handle cannot connect error."""
    instance = cfupdate_flow.return_value

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )

    instance.list_zones.side_effect = pycfdns.ComunicationException()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_form_invalid_auth(
    menuai: menuai, cfupdate_flow: MagicMock
) -> None:
    """Test we handle invalid auth error."""
    instance = cfupdate_flow.return_value

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )

    instance.list_zones.side_effect = pycfdns.AuthenticationException()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_form_unexpected_exception(
    menuai: menuai, cfupdate_flow: MagicMock
) -> None:
    """Test we handle unexpected exception."""
    instance = cfupdate_flow.return_value

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={CONF_SOURCE: SOURCE_USER}
    )

    instance.list_zones.side_effect = Exception()
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_user_form_single_instance_allowed(menuai: menuai) -> None:
    """Test that configuring more than one instance is rejected."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_CONFIG)
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={CONF_SOURCE: SOURCE_USER},
        data=USER_INPUT,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_reauth_flow(menuai: menuai, cfupdate_flow: MagicMock) -> None:
    """Test the reauthentication configuration flow."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_CONFIG)
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch_async_setup_entry() as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: "other_token"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    assert entry.data[CONF_API_TOKEN] == "other_token"
    assert entry.data[CONF_ZONE] == ENTRY_CONFIG[CONF_ZONE]
    assert entry.data[CONF_RECORDS] == ENTRY_CONFIG[CONF_RECORDS]

    assert len(mock_setup_entry.mock_calls) == 1
