"""Define tests for the LG Netcast config flow."""

from datetime import timedelta
from unittest.mock import DEFAULT, patch

from menuai import data_entry_flow
from menuai.components.lg_netcast.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import (
    CONF_ACCESS_TOKEN,
    CONF_HOST,
    CONF_ID,
    CONF_MODEL,
    CONF_NAME,
)
from menuai.core import menuai

from . import (
    FAKE_PIN,
    FRIENDLY_NAME,
    IP_ADDRESS,
    MODEL_NAME,
    UNIQUE_ID,
    _patch_lg_netcast,
)


async def test_show_form(menuai: menuai) -> None:
    """Test that the form is served with no input."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_user_invalid_host(menuai: menuai) -> None:
    """Test that errors are shown when the host is invalid."""
    with _patch_lg_netcast():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: "invalid/host"}
        )

        assert result["errors"] == {CONF_HOST: "invalid_host"}


async def test_manual_host(menuai: menuai) -> None:
    """Test manual host configuration."""
    with _patch_lg_netcast():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: IP_ADDRESS}
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "authorize"
        assert not result["errors"]

        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        assert result2["type"] == data_entry_flow.FlowResultType.FORM
        assert result2["step_id"] == "authorize"
        assert result2["errors"] is not None
        assert result2["errors"][CONF_ACCESS_TOKEN] == "invalid_access_token"

        result3 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ACCESS_TOKEN: FAKE_PIN}
        )

        assert result3["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result3["title"] == FRIENDLY_NAME
        assert result3["data"] == {
            CONF_HOST: IP_ADDRESS,
            CONF_ACCESS_TOKEN: FAKE_PIN,
            CONF_NAME: FRIENDLY_NAME,
            CONF_MODEL: MODEL_NAME,
            CONF_ID: UNIQUE_ID,
        }


async def test_manual_host_no_connection_during_authorize(menuai: menuai) -> None:
    """Test manual host configuration."""
    with _patch_lg_netcast(fail_connection=True):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: IP_ADDRESS}
        )

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "cannot_connect"


async def test_manual_host_invalid_details_during_authorize(
    menuai: menuai,
) -> None:
    """Test manual host configuration."""
    with _patch_lg_netcast(invalid_details=True):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: IP_ADDRESS}
        )

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "cannot_connect"


async def test_manual_host_unsuccessful_details_response(menuai: menuai) -> None:
    """Test manual host configuration."""
    with _patch_lg_netcast(always_404=True):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: IP_ADDRESS}
        )

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "cannot_connect"


async def test_manual_host_no_unique_id_response(menuai: menuai) -> None:
    """Test manual host configuration."""
    with _patch_lg_netcast(no_unique_id=True):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: IP_ADDRESS}
        )

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "invalid_host"


async def test_invalid_session_id(menuai: menuai) -> None:
    """Test Invalid Session ID."""
    with _patch_lg_netcast(session_error=True):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: IP_ADDRESS}
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "authorize"
        assert not result["errors"]

        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ACCESS_TOKEN: FAKE_PIN}
        )

        assert result2["type"] == data_entry_flow.FlowResultType.FORM
        assert result2["step_id"] == "authorize"
        assert result2["errors"] is not None
        assert result2["errors"]["base"] == "cannot_connect"


async def test_display_access_token_aborted(menuai: menuai) -> None:
    """Test Access token display is cancelled."""

    def _async_track_time_interval(
        menuai: menuai,
        action,
        interval: timedelta,
        *,
        name=None,
        cancel_on_shutdown=None,
    ):
        menuai.async_create_task(action())
        return DEFAULT

    with (
        _patch_lg_netcast(session_error=True),
        patch(
            "menuai.components.lg_netcast.config_flow.async_track_time_interval"
        ) as mock_interval,
    ):
        mock_interval.side_effect = _async_track_time_interval
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: IP_ADDRESS}
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "authorize"
        assert not result["errors"]

        assert mock_interval.called

        menuai.config_entries.flow.async_abort(result["flow_id"])
        assert mock_interval.return_value.called
