"""Test the WeatherflowCloud config flow."""

import pytest

from menuai import config_entries
from menuai.components.weatherflow_cloud.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_API_TOKEN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_config(menuai: menuai, mock_get_stations) -> None:
    """Test the config flow for the ideal case."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_TOKEN: "string",
        },
    )

    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_config_flow_abort(menuai: menuai, mock_get_stations) -> None:
    """Test an abort case."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_TOKEN: "same_same",
        },
    )
    entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_TOKEN: "same_same",
        },
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("mock_fixture", "expected_error"),
    [
        ("mock_get_stations_500_error", "cannot_connect"),
        ("mock_get_stations_401_error", "invalid_api_key"),
    ],
)
async def test_config_errors(
    menuai: menuai,
    request: pytest.FixtureRequest,
    expected_error: str,
    mock_fixture: str,
    mock_get_stations,
) -> None:
    """Test the config flow for various error scenarios."""
    mock_get_stations_bad = request.getfixturevalue(mock_fixture)
    with mock_get_stations_bad:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {}

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: "string"},
        )
        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": expected_error}

    with mock_get_stations:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_TOKEN: "string"},
        )
        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_reauth(menuai: menuai, mock_get_stations_401_error) -> None:
    """Test a reauth_flow."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_TOKEN: "same_same",
        },
    )
    entry.add_to_menuai(menuai)

    assert not await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR

    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_API_TOKEN: "SAME_SAME"}
    )

    assert result["reason"] == "reauth_successful"
    assert result["type"] is FlowResultType.ABORT
    assert entry.data[CONF_API_TOKEN] == "SAME_SAME"
