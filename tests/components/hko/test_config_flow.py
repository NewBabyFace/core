"""Test the Hong Kong Observatory config flow."""

from unittest.mock import patch

from hko import HKOError

from menuai.components.hko.const import DEFAULT_LOCATION, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_LOCATION
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_config_flow_default(menuai: menuai) -> None:
    """Test user config flow with default fields."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER
    assert "flow_id" in result

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_LOCATION: DEFAULT_LOCATION},
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == DEFAULT_LOCATION
    assert result2["result"].unique_id == DEFAULT_LOCATION
    assert result2["data"][CONF_LOCATION] == DEFAULT_LOCATION


async def test_config_flow_cannot_connect(menuai: menuai) -> None:
    """Test user config flow without connection to the API."""
    with patch("menuai.components.hko.config_flow.HKO.weather") as client_mock:
        client_mock.side_effect = HKOError()
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={CONF_LOCATION: DEFAULT_LOCATION},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"

        client_mock.side_effect = None

        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={CONF_LOCATION: DEFAULT_LOCATION},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["result"].unique_id == DEFAULT_LOCATION
        assert result["data"][CONF_LOCATION] == DEFAULT_LOCATION


async def test_config_flow_timeout(menuai: menuai) -> None:
    """Test user config flow with timedout connection to the API."""
    with patch("menuai.components.hko.config_flow.HKO.weather") as client_mock:
        client_mock.side_effect = TimeoutError()
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={CONF_LOCATION: DEFAULT_LOCATION},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "unknown"

        client_mock.side_effect = None

        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={CONF_LOCATION: DEFAULT_LOCATION},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["result"].unique_id == DEFAULT_LOCATION
        assert result["data"][CONF_LOCATION] == DEFAULT_LOCATION


async def test_config_flow_already_configured(menuai: menuai) -> None:
    """Test user config flow with two equal entries."""
    r1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert r1["type"] is FlowResultType.FORM
    assert r1["step_id"] == SOURCE_USER
    assert "flow_id" in r1
    result1 = await menuai.config_entries.flow.async_configure(
        r1["flow_id"],
        user_input={CONF_LOCATION: DEFAULT_LOCATION},
    )
    assert result1["type"] is FlowResultType.CREATE_ENTRY

    r2 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert r2["type"] is FlowResultType.FORM
    assert r2["step_id"] == SOURCE_USER
    assert "flow_id" in r2
    result2 = await menuai.config_entries.flow.async_configure(
        r2["flow_id"],
        user_input={CONF_LOCATION: DEFAULT_LOCATION},
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
