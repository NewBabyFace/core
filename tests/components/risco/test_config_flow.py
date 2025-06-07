"""Test the Risco config flow."""

from unittest.mock import PropertyMock, patch

import pytest
import voluptuous as vol

from menuai import config_entries
from menuai.components.risco.config_flow import (
    CannotConnectError,
    UnauthorizedError,
)
from menuai.components.risco.const import CONF_COMMUNICATION_DELAY, DOMAIN
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

TEST_SITE_NAME = "test-site-name"
TEST_CLOUD_DATA = {
    "username": "test-username",
    "password": "test-password",
    "pin": "1234",
}

TEST_LOCAL_DATA = {
    "host": "test-host",
    "port": 5004,
    "pin": "1234",
}

TEST_RISCO_TO_HA = {
    "arm": "armed_away",
    "partial_arm": "armed_home",
    "A": "armed_home",
    "B": "armed_home",
    "C": "armed_night",
    "D": "armed_night",
}

TEST_HA_TO_RISCO = {
    "armed_away": "arm",
    "armed_home": "partial_arm",
    "armed_night": "C",
}

TEST_OPTIONS = {
    "code_arm_required": True,
    "code_disarm_required": True,
}

TEST_ADVANCED_OPTIONS = {
    "scan_interval": 10,
    "concurrency": 3,
}


async def test_cloud_form(menuai: menuai) -> None:
    """Test we get the cloud form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "cloud"}
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {}

    with (
        patch(
            "menuai.components.risco.config_flow.RiscoCloud.login",
            return_value=True,
        ),
        patch(
            "menuai.components.risco.config_flow.RiscoCloud.site_name",
            new_callable=PropertyMock(return_value=TEST_SITE_NAME),
        ),
        patch(
            "menuai.components.risco.config_flow.RiscoCloud.close"
        ) as mock_close,
        patch(
            "menuai.components.risco.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"], TEST_CLOUD_DATA
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == TEST_SITE_NAME
    assert result3["data"] == TEST_CLOUD_DATA
    assert len(mock_setup_entry.mock_calls) == 1
    mock_close.assert_awaited_once()


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (UnauthorizedError, "invalid_auth"),
        (CannotConnectError, "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_cloud_error(menuai: menuai, login_with_error, error) -> None:
    """Test we handle config flow errors."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "cloud"}
    )

    with patch(
        "menuai.components.risco.config_flow.RiscoCloud.close"
    ) as mock_close:
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"], TEST_CLOUD_DATA
        )

    mock_close.assert_awaited_once()
    assert result3["type"] is FlowResultType.FORM
    assert result3["errors"] == {"base": error}


async def test_form_cloud_already_exists(menuai: menuai) -> None:
    """Test that a flow with an existing username aborts."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_CLOUD_DATA["username"],
        data=TEST_CLOUD_DATA,
    )

    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "cloud"}
    )

    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"], TEST_CLOUD_DATA
    )

    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "already_configured"


async def test_form_reauth(
    menuai: menuai, cloud_config_entry: MockConfigEntry
) -> None:
    """Test reauthenticate."""

    result = await cloud_config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.risco.config_flow.RiscoCloud.login",
            return_value=True,
        ),
        patch(
            "menuai.components.risco.config_flow.RiscoCloud.site_name",
            new_callable=PropertyMock(return_value=TEST_SITE_NAME),
        ),
        patch(
            "menuai.components.risco.config_flow.RiscoCloud.close",
        ),
        patch(
            "menuai.components.risco.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {**TEST_CLOUD_DATA, CONF_PASSWORD: "new_password"}
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert cloud_config_entry.data[CONF_PASSWORD] == "new_password"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_reauth_with_new_username(
    menuai: menuai, cloud_config_entry: MockConfigEntry
) -> None:
    """Test reauthenticate with new username."""

    result = await cloud_config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.risco.config_flow.RiscoCloud.login",
            return_value=True,
        ),
        patch(
            "menuai.components.risco.config_flow.RiscoCloud.site_name",
            new_callable=PropertyMock(return_value=TEST_SITE_NAME),
        ),
        patch(
            "menuai.components.risco.config_flow.RiscoCloud.close",
        ),
        patch(
            "menuai.components.risco.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {**TEST_CLOUD_DATA, CONF_USERNAME: "new_user"}
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert cloud_config_entry.data[CONF_USERNAME] == "new_user"
    assert cloud_config_entry.unique_id == "new_user"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_local_form(menuai: menuai) -> None:
    """Test we get the local form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "local"}
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {}

    with (
        patch(
            "menuai.components.risco.config_flow.RiscoLocal.connect",
            return_value=True,
        ),
        patch(
            "menuai.components.risco.config_flow.RiscoLocal.id",
            new_callable=PropertyMock(return_value=TEST_SITE_NAME),
        ),
        patch(
            "menuai.components.risco.config_flow.RiscoLocal.disconnect"
        ) as mock_close,
        patch(
            "menuai.components.risco.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"], TEST_LOCAL_DATA
        )
        await menuai.async_block_till_done()

    expected_data = {
        **TEST_LOCAL_DATA,
        "type": "local",
        CONF_COMMUNICATION_DELAY: 0,
    }
    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == TEST_SITE_NAME
    assert result3["data"] == expected_data
    assert len(mock_setup_entry.mock_calls) == 1
    mock_close.assert_awaited_once()


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (UnauthorizedError, "invalid_auth"),
        (CannotConnectError, "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_local_error(menuai: menuai, connect_with_error, error) -> None:
    """Test we handle config flow errors."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "local"}
    )

    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"], TEST_LOCAL_DATA
    )

    assert result3["type"] is FlowResultType.FORM
    assert result3["errors"] == {"base": error}


async def test_form_local_already_exists(menuai: menuai) -> None:
    """Test that a flow with an existing host aborts."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_SITE_NAME,
        data=TEST_LOCAL_DATA,
    )

    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "local"}
    )

    with (
        patch(
            "menuai.components.risco.config_flow.RiscoLocal.connect",
            return_value=True,
        ),
        patch(
            "menuai.components.risco.config_flow.RiscoLocal.id",
            new_callable=PropertyMock(return_value=TEST_SITE_NAME),
        ),
        patch(
            "menuai.components.risco.config_flow.RiscoLocal.disconnect",
        ),
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"], TEST_LOCAL_DATA
        )

    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "already_configured"


async def test_options_flow(menuai: menuai) -> None:
    """Test options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_CLOUD_DATA["username"],
        data=TEST_CLOUD_DATA,
    )

    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input=TEST_OPTIONS,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "risco_to_ha"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input=TEST_RISCO_TO_HA,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ha_to_risco"

    with patch("menuai.components.risco.async_setup_entry", return_value=True):
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input=TEST_HA_TO_RISCO,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        **TEST_OPTIONS,
        "risco_states_to_ha": TEST_RISCO_TO_HA,
        "ha_states_to_risco": TEST_HA_TO_RISCO,
    }


async def test_advanced_options_flow(menuai: menuai) -> None:
    """Test options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_CLOUD_DATA["username"],
        data=TEST_CLOUD_DATA,
    )

    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(
        entry.entry_id, context={"show_advanced_options": True}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert "concurrency" in result["data_schema"].schema
    assert "scan_interval" in result["data_schema"].schema
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input={**TEST_OPTIONS, **TEST_ADVANCED_OPTIONS}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "risco_to_ha"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input=TEST_RISCO_TO_HA,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ha_to_risco"

    with patch("menuai.components.risco.async_setup_entry", return_value=True):
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input=TEST_HA_TO_RISCO,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        **TEST_OPTIONS,
        **TEST_ADVANCED_OPTIONS,
        "risco_states_to_ha": TEST_RISCO_TO_HA,
        "ha_states_to_risco": TEST_HA_TO_RISCO,
    }


async def test_ha_to_risco_schema(menuai: menuai) -> None:
    """Test that the schema for the ha-to-risco mapping step is generated properly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_CLOUD_DATA["username"],
        data=TEST_CLOUD_DATA,
    )

    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input=TEST_OPTIONS,
    )
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input=TEST_RISCO_TO_HA,
    )

    # Test an HA state that isn't used
    with pytest.raises(vol.error.Invalid):
        await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={**TEST_HA_TO_RISCO, "armed_custom_bypass": "D"},
        )

    # Test a combo that can't be selected
    with pytest.raises(vol.error.Invalid):
        await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={**TEST_HA_TO_RISCO, "armed_night": "A"},
        )
