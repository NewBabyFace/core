"""Test the P1 Monitor config flow."""

from unittest.mock import patch

from p1monitor import P1MonitorError

from menuai.components.p1_monitor.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_full_user_flow(menuai: menuai) -> None:
    """Test the full user configuration flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    with (
        patch(
            "menuai.components.p1_monitor.config_flow.P1Monitor.smartmeter"
        ) as mock_p1monitor,
        patch(
            "menuai.components.p1_monitor.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HOST: "example.com", CONF_PORT: 80},
        )

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("title") == "P1 Monitor"
    assert result2.get("data") == {CONF_HOST: "example.com", CONF_PORT: 80}
    assert isinstance(result2["data"][CONF_PORT], int)

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_p1monitor.mock_calls) == 1


async def test_api_error(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    with patch(
        "menuai.components.p1_monitor.coordinator.P1Monitor.smartmeter",
        side_effect=P1MonitorError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={CONF_HOST: "example.com", CONF_PORT: 80},
        )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {"base": "cannot_connect"}
