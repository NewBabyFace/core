"""Test the SwitchBee Smart Home config flow."""

import json
from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.switchbee.config_flow import SwitchBeeError
from menuai.components.switchbee.const import DOMAIN
from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import MOCK_FAILED_TO_LOGIN_MSG, MOCK_INVALID_TOKEN_MGS

from tests.common import MockConfigEntry, async_load_fixture


@pytest.mark.parametrize("test_cucode_in_coordinator_data", [False, True])
async def test_form(menuai: menuai, test_cucode_in_coordinator_data) -> None:
    """Test we get the form."""

    coordinator_data = json.loads(
        await async_load_fixture(menuai, "switchbee.json", DOMAIN)
    )

    if test_cucode_in_coordinator_data:
        coordinator_data["data"]["cuCode"] = "300F123456"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "switchbee.api.polling.CentralUnitPolling.get_configuration",
            return_value=coordinator_data,
        ),
        patch(
            "menuai.components.switchbee.async_setup_entry",
            return_value=True,
        ),
        patch(
            "switchbee.api.polling.CentralUnitPolling.fetch_states", return_value=None
        ),
        patch("switchbee.api.polling.CentralUnitPolling._login", return_value=None),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "1.1.1.1"
    assert result2["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_USERNAME: "test-username",
        CONF_PASSWORD: "test-password",
    }


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "switchbee.api.polling.CentralUnitPolling._login",
        side_effect=SwitchBeeError(MOCK_FAILED_TO_LOGIN_MSG),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "switchbee.api.polling.CentralUnitPolling._login",
        side_effect=SwitchBeeError(MOCK_INVALID_TOKEN_MGS),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unknown_error(menuai: menuai) -> None:
    """Test we handle an unknown error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "switchbee.api.polling.CentralUnitPolling._login",
        side_effect=Exception,
    ):
        form_result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert form_result["type"] is FlowResultType.FORM
    assert form_result["errors"] == {"base": "unknown"}


async def test_form_entry_exists(menuai: menuai) -> None:
    """Test we handle an already existing entry."""

    coordinator_data = json.loads(
        await async_load_fixture(menuai, "switchbee.json", DOMAIN)
    )
    MockConfigEntry(
        unique_id="a8:21:08:e7:67:b6",
        domain=DOMAIN,
        data={
            CONF_HOST: "1.1.1.1",
            CONF_USERNAME: "test-username",
            CONF_PASSWORD: "test-password",
        },
        title="1.1.1.1",
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch("switchbee.api.polling.CentralUnitPolling._login", return_value=None),
        patch(
            "menuai.components.switchbee.async_setup_entry",
            return_value=True,
        ),
        patch(
            "switchbee.api.polling.CentralUnitPolling.get_configuration",
            return_value=coordinator_data,
        ),
        patch(
            "switchbee.api.polling.CentralUnitPolling.fetch_states", return_value=None
        ),
    ):
        form_result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.2.2.2",
                CONF_USERNAME: "test-username",
                CONF_PASSWORD: "test-password",
            },
        )

    assert form_result["type"] is FlowResultType.ABORT
    assert form_result["reason"] == "already_configured"
