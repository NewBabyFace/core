"""Test the Yale Smart Living config flow."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from yalesmartalarmclient.exceptions import AuthenticationError, UnknownError

from menuai import config_entries
from menuai.components.yale_smart_alarm.const import DOMAIN
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
            "menuai.components.yale_smart_alarm.config_flow.YaleSmartAlarmClient",
        ),
        patch(
            "menuai.components.yale_smart_alarm.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "area_id": "1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test-username"
    assert result2["data"] == {
        "username": "test-username",
        "password": "test-password",
        "area_id": "1",
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("sideeffect", "p_error"),
    [
        (AuthenticationError, "invalid_auth"),
        (ConnectionError, "cannot_connect"),
        (TimeoutError, "cannot_connect"),
        (UnknownError, "cannot_connect"),
    ],
)
async def test_form_invalid_auth(
    menuai: menuai, sideeffect: Exception, p_error: str
) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.yale_smart_alarm.config_flow.YaleSmartAlarmClient",
        side_effect=sideeffect,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "area_id": "1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": p_error}

    with (
        patch(
            "menuai.components.yale_smart_alarm.config_flow.YaleSmartAlarmClient",
        ),
        patch(
            "menuai.components.yale_smart_alarm.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "area_id": "1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test-username"
    assert result2["data"] == {
        "username": "test-username",
        "password": "test-password",
        "area_id": "1",
    }


async def test_reauth_flow(menuai: menuai) -> None:
    """Test a reauthentication flow."""
    entry = MockConfigEntry(
        title="test-username",
        domain=DOMAIN,
        unique_id="test-username",
        data={
            "username": "test-username",
            "password": "test-password",
            "area_id": "1",
        },
        version=2,
        minor_version=2,
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.yale_smart_alarm.config_flow.YaleSmartAlarmClient",
        ) as mock_yale,
        patch(
            "menuai.components.yale_smart_alarm.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "password": "new-test-password",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert entry.data == {
        "username": "test-username",
        "password": "new-test-password",
        "area_id": "1",
    }

    assert len(mock_yale.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("sideeffect", "p_error"),
    [
        (AuthenticationError, "invalid_auth"),
        (ConnectionError, "cannot_connect"),
        (TimeoutError, "cannot_connect"),
        (UnknownError, "cannot_connect"),
    ],
)
async def test_reauth_flow_error(
    menuai: menuai, sideeffect: Exception, p_error: str
) -> None:
    """Test a reauthentication flow."""
    entry = MockConfigEntry(
        title="test-username",
        domain=DOMAIN,
        unique_id="test-username",
        data={
            "username": "test-username",
            "password": "test-password",
            "area_id": "1",
        },
        version=2,
        minor_version=2,
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    with patch(
        "menuai.components.yale_smart_alarm.config_flow.YaleSmartAlarmClient",
        side_effect=sideeffect,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "password": "wrong-password",
            },
        )
        await menuai.async_block_till_done()

    assert result2["step_id"] == "reauth_confirm"
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": p_error}

    with (
        patch(
            "menuai.components.yale_smart_alarm.config_flow.YaleSmartAlarmClient",
            return_value="",
        ),
        patch(
            "menuai.components.yale_smart_alarm.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "password": "new-test-password",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert entry.data == {
        "username": "test-username",
        "password": "new-test-password",
        "area_id": "1",
    }


async def test_reconfigure(menuai: menuai) -> None:
    """Test reconfigure config flow."""
    entry = MockConfigEntry(
        title="test-username",
        domain=DOMAIN,
        unique_id="test-username",
        data={
            "username": "test-username",
            "password": "test-password",
            "area_id": "1",
        },
        version=2,
        minor_version=2,
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)

    with (
        patch(
            "menuai.components.yale_smart_alarm.config_flow.YaleSmartAlarmClient",
            return_value="",
        ),
        patch(
            "menuai.components.yale_smart_alarm.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "new-test-password",
                "area_id": "2",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reconfigure_successful"
    assert entry.data == {
        "username": "test-username",
        "password": "new-test-password",
        "area_id": "2",
    }


async def test_reconfigure_username_exist(menuai: menuai) -> None:
    """Test reconfigure config flow abort other username already exist."""
    entry = MockConfigEntry(
        title="test-username",
        domain=DOMAIN,
        unique_id="test-username",
        data={
            "username": "test-username",
            "password": "test-password",
            "area_id": "1",
        },
        version=2,
        minor_version=2,
    )
    entry.add_to_menuai(menuai)
    entry2 = MockConfigEntry(
        title="other-username",
        domain=DOMAIN,
        unique_id="other-username",
        data={
            "username": "other-username",
            "password": "test-password",
            "area_id": "1",
        },
        version=2,
        minor_version=2,
    )
    entry2.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)

    with (
        patch(
            "menuai.components.yale_smart_alarm.config_flow.YaleSmartAlarmClient",
            return_value="",
        ),
        patch(
            "menuai.components.yale_smart_alarm.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "other-username",
                "password": "test-password",
                "area_id": "1",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unique_id_exists"}

    with (
        patch(
            "menuai.components.yale_smart_alarm.config_flow.YaleSmartAlarmClient",
            return_value="",
        ),
        patch(
            "menuai.components.yale_smart_alarm.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "other-new-username",
                "password": "test-password",
                "area_id": "1",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {
        "username": "other-new-username",
        "password": "test-password",
        "area_id": "1",
    }


@pytest.mark.parametrize(
    ("sideeffect", "p_error"),
    [
        (AuthenticationError, "invalid_auth"),
        (ConnectionError, "cannot_connect"),
        (TimeoutError, "cannot_connect"),
        (UnknownError, "cannot_connect"),
    ],
)
async def test_reconfigure_flow_error(
    menuai: menuai, sideeffect: Exception, p_error: str
) -> None:
    """Test a reauthentication flow."""
    entry = MockConfigEntry(
        title="test-username",
        domain=DOMAIN,
        unique_id="test-username",
        data={
            "username": "test-username",
            "password": "test-password",
            "area_id": "1",
        },
        version=2,
        minor_version=2,
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)

    with patch(
        "menuai.components.yale_smart_alarm.config_flow.YaleSmartAlarmClient",
        side_effect=sideeffect,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "update-password",
                "area_id": "1",
            },
        )
        await menuai.async_block_till_done()

    assert result["step_id"] == "reconfigure"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": p_error}

    with (
        patch(
            "menuai.components.yale_smart_alarm.config_flow.YaleSmartAlarmClient",
            return_value="",
        ),
        patch(
            "menuai.components.yale_smart_alarm.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "new-test-password",
                "area_id": "1",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {
        "username": "test-username",
        "password": "new-test-password",
        "area_id": "1",
    }


async def test_options_flow(
    menuai: menuai,
    load_config_entry: tuple[MockConfigEntry, Mock],
) -> None:
    """Test options config flow."""
    entry = load_config_entry[0]

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    with patch(
        "menuai.components.yale_smart_alarm.coordinator.YaleSmartAlarmClient",
        return_value=load_config_entry[1],
    ):
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"lock_code_digits": 4},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"lock_code_digits": 4}

    assert entry.state == config_entries.ConfigEntryState.LOADED
