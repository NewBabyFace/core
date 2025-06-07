"""Test the Sensibo config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from pysensibo import AuthenticationError, SensiboData, SensiboError
import pytest

from menuai import config_entries
from menuai.components.sensibo.const import DOMAIN
from menuai.const import CONF_API_KEY
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_basic_setup(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_client: MagicMock
) -> None:
    """Test we get and complete the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_API_KEY: "1234567890",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["version"] == 2
    assert result["title"] == "firstnamelastname"
    assert result["result"].unique_id == "firstnamelastname"
    assert result["data"] == {
        CONF_API_KEY: "1234567890",
    }

    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("error_message", "p_error"),
    [
        (AuthenticationError, "invalid_auth"),
        (SensiboError, "cannot_connect"),
    ],
)
async def test_flow_fails(
    menuai: menuai, mock_client: MagicMock, error_message: Exception, p_error: str
) -> None:
    """Test config flow errors."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == config_entries.SOURCE_USER

    mock_client.async_get_devices.side_effect = error_message

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_KEY: "1234567890",
        },
    )

    assert result["errors"] == {"base": p_error}

    mock_client.async_get_devices.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_KEY: "1234567890",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "firstnamelastname"
    assert result["data"] == {
        CONF_API_KEY: "1234567890",
    }


async def test_flow_get_no_devices(
    menuai: menuai,
    mock_client: MagicMock,
    get_data: tuple[SensiboData, dict[str, Any], dict[str, Any]],
) -> None:
    """Test config flow get no devices from api."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == config_entries.SOURCE_USER

    mock_client.async_get_devices.return_value = {"result": []}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_KEY: "1234567890",
        },
    )

    assert result["errors"] == {"base": "no_devices"}

    mock_client.async_get_devices.return_value = get_data[2]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_KEY: "1234567890",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "firstnamelastname"
    assert result["data"] == {
        CONF_API_KEY: "1234567890",
    }


async def test_flow_get_no_username(
    menuai: menuai,
    mock_client: MagicMock,
    get_data: tuple[SensiboData, dict[str, Any], dict[str, Any]],
) -> None:
    """Test config flow get no username from api."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == config_entries.SOURCE_USER

    mock_client.async_get_me.return_value = {"result": {}}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_KEY: "1234567890",
        },
    )

    assert result2["errors"] == {"base": "no_username"}

    mock_client.async_get_me.return_value = get_data[1]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_KEY: "1234567890",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "firstnamelastname"
    assert result["data"] == {
        CONF_API_KEY: "1234567890",
    }


async def test_reauth_flow(menuai: menuai, mock_client: MagicMock) -> None:
    """Test a reauthentication flow."""
    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        unique_id="firstnamelastname",
        data={CONF_API_KEY: "1234567890"},
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "1234567890"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data == {CONF_API_KEY: "1234567890"}


@pytest.mark.parametrize(
    ("sideeffect", "p_error"),
    [
        (AuthenticationError, "invalid_auth"),
        (SensiboError, "cannot_connect"),
    ],
)
async def test_reauth_flow_error(
    menuai: menuai, sideeffect: Exception, p_error: str, mock_client: MagicMock
) -> None:
    """Test a reauthentication flow with error."""
    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        unique_id="firstnamelastname",
        data={CONF_API_KEY: "1234567890"},
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    mock_client.async_get_devices.side_effect = sideeffect

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "1234567890"},
    )

    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": p_error}

    mock_client.async_get_devices.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "1234567890"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data == {CONF_API_KEY: "1234567890"}


@pytest.mark.parametrize(
    ("get_devices", "get_me", "p_error"),
    [
        (
            {"result": [{"id": "xyzxyz"}, {"id": "abcabc"}]},
            {"result": {}},
            "no_username",
        ),
        (
            {"result": []},
            {"result": {"username": "firstnamelastname"}},
            "no_devices",
        ),
        (
            {"result": [{"id": "xyzxyz"}, {"id": "abcabc"}]},
            {"result": {"username": "firstnamelastname2"}},
            "incorrect_api_key",
        ),
    ],
)
async def test_flow_reauth_no_username_or_device(
    menuai: menuai,
    get_devices: dict[str, Any],
    get_me: dict[str, Any],
    p_error: str,
    mock_client: MagicMock,
    get_data: tuple[SensiboData, dict[str, Any], dict[str, Any]],
) -> None:
    """Test reauth flow with errors from api."""
    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        unique_id="firstnamelastname",
        data={CONF_API_KEY: "1234567890"},
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    mock_client.async_get_devices.return_value = get_devices
    mock_client.async_get_me.return_value = get_me

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_KEY: "1234567890",
        },
    )

    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": p_error}

    mock_client.async_get_devices.return_value = get_data[2]
    mock_client.async_get_me.return_value = get_data[1]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "1234567890"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data == {CONF_API_KEY: "1234567890"}


async def test_reconfigure_flow(menuai: menuai, mock_client: MagicMock) -> None:
    """Test a reconfigure flow."""
    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        unique_id="firstnamelastname",
        data={CONF_API_KEY: "1234567890"},
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)
    assert result["step_id"] == "reconfigure"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "1234567890"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {CONF_API_KEY: "1234567890"}


@pytest.mark.parametrize(
    ("sideeffect", "p_error"),
    [
        (AuthenticationError, "invalid_auth"),
        (SensiboError, "cannot_connect"),
    ],
)
async def test_reconfigure_flow_error(
    menuai: menuai,
    sideeffect: Exception,
    p_error: str,
    mock_client: MagicMock,
) -> None:
    """Test a reconfigure flow with error."""
    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        unique_id="firstnamelastname",
        data={CONF_API_KEY: "1234567890"},
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)

    mock_client.async_get_devices.side_effect = sideeffect

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "1234567890"},
    )

    assert result["step_id"] == "reconfigure"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": p_error}

    mock_client.async_get_devices.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "1234567890"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {CONF_API_KEY: "1234567890"}


@pytest.mark.parametrize(
    ("get_devices", "get_me", "p_error"),
    [
        (
            {"result": [{"id": "xyzxyz"}, {"id": "abcabc"}]},
            {"result": {}},
            "no_username",
        ),
        (
            {"result": []},
            {"result": {"username": "firstnamelastname"}},
            "no_devices",
        ),
        (
            {"result": [{"id": "xyzxyz"}, {"id": "abcabc"}]},
            {"result": {"username": "firstnamelastname2"}},
            "incorrect_api_key",
        ),
    ],
)
async def test_flow_reconfigure_no_username_or_device(
    menuai: menuai,
    get_devices: dict[str, Any],
    get_me: dict[str, Any],
    p_error: str,
    mock_client: MagicMock,
    get_data: tuple[SensiboData, dict[str, Any], dict[str, Any]],
) -> None:
    """Test reconfigure flow with errors from api."""
    entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        unique_id="firstnamelastname",
        data={CONF_API_KEY: "1234567890"},
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    mock_client.async_get_devices.return_value = get_devices
    mock_client.async_get_me.return_value = get_me

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_KEY: "1234567890",
        },
    )

    assert result["step_id"] == "reconfigure"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": p_error}

    mock_client.async_get_devices.return_value = get_data[2]
    mock_client.async_get_me.return_value = get_data[1]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "1234567890"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {CONF_API_KEY: "1234567890"}
