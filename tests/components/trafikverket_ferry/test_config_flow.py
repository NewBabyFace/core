"""Test the Trafikverket Ferry config flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytrafikverket.exceptions import InvalidAuthentication, NoFerryFound

from menuai import config_entries
from menuai.components.trafikverket_ferry.const import (
    CONF_FROM,
    CONF_TIME,
    CONF_TO,
    DOMAIN,
)
from menuai.const import CONF_API_KEY, CONF_NAME, CONF_WEEKDAY, WEEKDAYS
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.trafikverket_ferry.config_flow.TrafikverketFerry.async_get_next_ferry_stop",
        ),
        patch(
            "menuai.components.trafikverket_ferry.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "1234567890",
                CONF_FROM: "Ekerö",
                CONF_TO: "Slagsta",
                CONF_TIME: "10:00",
                CONF_WEEKDAY: ["mon", "fri"],
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Ekerö to Slagsta at 10:00"
    assert result2["data"] == {
        "api_key": "1234567890",
        "name": "Ekerö to Slagsta at 10:00",
        "from": "Ekerö",
        "to": "Slagsta",
        "time": "10:00",
        "weekday": ["mon", "fri"],
    }
    assert len(mock_setup_entry.mock_calls) == 1
    assert result2["result"].unique_id == "eker\u00f6-slagsta-10:00-['mon', 'fri']"


@pytest.mark.parametrize(
    ("side_effect", "base_error"),
    [
        (
            InvalidAuthentication,
            "invalid_auth",
        ),
        (
            NoFerryFound,
            "invalid_route",
        ),
        (
            Exception,
            "cannot_connect",
        ),
    ],
)
async def test_flow_fails(
    menuai: menuai, side_effect: str, base_error: str
) -> None:
    """Test config flow errors."""
    result4 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result4["type"] is FlowResultType.FORM
    assert result4["step_id"] == config_entries.SOURCE_USER

    with patch(
        "menuai.components.trafikverket_ferry.config_flow.TrafikverketFerry.async_get_next_ferry_stop",
        side_effect=side_effect(),
    ):
        result4 = await menuai.config_entries.flow.async_configure(
            result4["flow_id"],
            user_input={
                CONF_API_KEY: "1234567890",
                CONF_FROM: "Ekerö",
                CONF_TO: "Slagsta",
                CONF_TIME: "00:00",
            },
        )

    assert result4["errors"] == {"base": base_error}


async def test_reauth_flow(menuai: menuai) -> None:
    """Test a reauthentication flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_KEY: "1234567890",
            CONF_NAME: "Ekerö to Slagsta at 10:00",
            CONF_FROM: "Ekerö",
            CONF_TO: "Slagsta",
            CONF_TIME: "10:00",
            CONF_WEEKDAY: WEEKDAYS,
        },
        unique_id=f"eker\u00f6-slagsta-10:00-{WEEKDAYS}",
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.trafikverket_ferry.config_flow.TrafikverketFerry.async_get_next_ferry_stop",
        ),
        patch(
            "menuai.components.trafikverket_ferry.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "1234567891"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert entry.data == {
        "api_key": "1234567891",
        "name": "Ekerö to Slagsta at 10:00",
        "from": "Ekerö",
        "to": "Slagsta",
        "time": "10:00",
        "weekday": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    }


@pytest.mark.parametrize(
    ("side_effect", "p_error"),
    [
        (
            InvalidAuthentication,
            "invalid_auth",
        ),
        (
            NoFerryFound,
            "invalid_route",
        ),
        (
            Exception,
            "cannot_connect",
        ),
    ],
)
async def test_reauth_flow_error(
    menuai: menuai, side_effect: Exception, p_error: str
) -> None:
    """Test a reauthentication flow with error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_KEY: "1234567890",
            CONF_NAME: "Ekerö to Slagsta at 10:00",
            CONF_FROM: "Ekerö",
            CONF_TO: "Slagsta",
            CONF_TIME: "10:00",
            CONF_WEEKDAY: WEEKDAYS,
        },
        unique_id=f"eker\u00f6-slagsta-10:00-{WEEKDAYS}",
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    with patch(
        "menuai.components.trafikverket_ferry.config_flow.TrafikverketFerry.async_get_next_ferry_stop",
        side_effect=side_effect(),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "1234567890"},
        )
        await menuai.async_block_till_done()

    assert result2["step_id"] == "reauth_confirm"
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": p_error}

    with (
        patch(
            "menuai.components.trafikverket_ferry.config_flow.TrafikverketFerry.async_get_next_ferry_stop",
        ),
        patch(
            "menuai.components.trafikverket_ferry.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "1234567891"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert entry.data == {
        "api_key": "1234567891",
        "name": "Ekerö to Slagsta at 10:00",
        "from": "Ekerö",
        "to": "Slagsta",
        "time": "10:00",
        "weekday": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    }
