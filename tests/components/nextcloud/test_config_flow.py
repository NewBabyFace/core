"""Tests for the Nextcloud config flow."""

from unittest.mock import patch

from nextcloudmonitor import (
    NextcloudMonitorAuthorizationError,
    NextcloudMonitorConnectionError,
    NextcloudMonitorRequestError,
)
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.nextcloud.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import VALID_CONFIG

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_user_create_entry(
    menuai: menuai, snapshot: SnapshotAssertion
) -> None:
    """Test that the user step works."""
    # start user flow
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    # test NextcloudMonitorAuthorizationError
    with patch(
        "menuai.components.nextcloud.config_flow.NextcloudMonitor",
        side_effect=NextcloudMonitorAuthorizationError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_CONFIG,
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}

    # test NextcloudMonitorConnectionError
    with patch(
        "menuai.components.nextcloud.config_flow.NextcloudMonitor",
        side_effect=NextcloudMonitorConnectionError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_CONFIG,
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "connection_error"}

    # test NextcloudMonitorRequestError
    with patch(
        "menuai.components.nextcloud.config_flow.NextcloudMonitor",
        side_effect=NextcloudMonitorRequestError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_CONFIG,
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "connection_error"}

    # test success
    with patch(
        "menuai.components.nextcloud.config_flow.NextcloudMonitor",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_CONFIG,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "https://my.nc_url.local"
    assert result["data"] == snapshot


async def test_user_already_configured(menuai: menuai) -> None:
    """Test that errors are shown when duplicates are added."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="https://my.nc_url.local",
        unique_id="nc_url",
        data=VALID_CONFIG,
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "menuai.components.nextcloud.config_flow.NextcloudMonitor",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_CONFIG,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(menuai: menuai, snapshot: SnapshotAssertion) -> None:
    """Test that the re-auth flow works."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="https://my.nc_url.local",
        unique_id="nc_url",
        data=VALID_CONFIG,
    )
    entry.add_to_menuai(menuai)

    # start reauth flow
    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    # test NextcloudMonitorAuthorizationError
    with patch(
        "menuai.components.nextcloud.config_flow.NextcloudMonitor",
        side_effect=NextcloudMonitorAuthorizationError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "other_user",
                CONF_PASSWORD: "other_password",
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "invalid_auth"}

    # test NextcloudMonitorConnectionError
    with patch(
        "menuai.components.nextcloud.config_flow.NextcloudMonitor",
        side_effect=NextcloudMonitorConnectionError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "other_user",
                CONF_PASSWORD: "other_password",
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "connection_error"}

    # test NextcloudMonitorRequestError
    with patch(
        "menuai.components.nextcloud.config_flow.NextcloudMonitor",
        side_effect=NextcloudMonitorRequestError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "other_user",
                CONF_PASSWORD: "other_password",
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "connection_error"}

    # test success
    with patch(
        "menuai.components.nextcloud.config_flow.NextcloudMonitor",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "other_user",
                CONF_PASSWORD: "other_password",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data == snapshot
