"""Test the MELCloud config flow."""

from http import HTTPStatus
from unittest.mock import patch

from aiohttp import ClientError, ClientResponseError
import pymelcloud
import pytest

from menuai import config_entries
from menuai.components.melcloud.const import DOMAIN
from menuai.const import CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.fixture
def mock_login():
    """Mock pymelcloud login."""
    with patch(
        "menuai.components.melcloud.config_flow.pymelcloud.login"
    ) as mock:
        mock.return_value = "test-token"
        yield mock


@pytest.fixture
def mock_get_devices():
    """Mock pymelcloud get_devices."""
    with patch(
        "menuai.components.melcloud.config_flow.pymelcloud.get_devices"
    ) as mock:
        mock.return_value = {
            pymelcloud.DEVICE_TYPE_ATA: [],
            pymelcloud.DEVICE_TYPE_ATW: [],
        }
        yield mock


@pytest.fixture
def mock_request_info():
    """Mock RequestInfo to create ClientResponseErrors."""
    with patch("aiohttp.RequestInfo") as mock_ri:
        mock_ri.return_value.real_url.return_value = ""
        yield mock_ri


async def test_form(menuai: menuai, mock_login, mock_get_devices) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "menuai.components.melcloud.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-email@test-domain.com", "password": "test-password"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test-email@test-domain.com"
    assert result2["data"] == {
        "username": "test-email@test-domain.com",
        "token": "test-token",
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("error", "reason"),
    [(ClientError(), "cannot_connect"), (TimeoutError(), "cannot_connect")],
)
async def test_form_errors(
    menuai: menuai, mock_login, mock_get_devices, error, reason
) -> None:
    """Test we handle cannot connect error."""
    mock_login.side_effect = error

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={"username": "test-email@test-domain.com", "password": "test-password"},
    )

    assert len(mock_login.mock_calls) == 1
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (HTTPStatus.UNAUTHORIZED, "invalid_auth"),
        (HTTPStatus.FORBIDDEN, "invalid_auth"),
        (HTTPStatus.INTERNAL_SERVER_ERROR, "cannot_connect"),
    ],
)
async def test_form_response_errors(
    menuai: menuai, mock_login, mock_get_devices, mock_request_info, error, message
) -> None:
    """Test we handle response errors."""
    mock_login.side_effect = ClientResponseError(mock_request_info(), (), status=error)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={"username": "test-email@test-domain.com", "password": "test-password"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == message


async def test_token_refresh(menuai: menuai, mock_login, mock_get_devices) -> None:
    """Re-configuration with existing username should refresh token."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test-email@test-domain.com", "token": "test-original-token"},
        unique_id="test-email@test-domain.com",
    )
    mock_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.melcloud.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                "username": "test-email@test-domain.com",
                "password": "test-password",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    await menuai.async_block_till_done()
    assert len(mock_setup_entry.mock_calls) == 0

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1

    entry = entries[0]
    assert entry.data["username"] == "test-email@test-domain.com"
    assert entry.data["token"] == "test-token"


async def test_token_reauthentication(
    menuai: menuai,
    mock_login,
    mock_get_devices,
) -> None:
    """Re-configuration with existing username should refresh token, if made invalid."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test-email@test-domain.com", "token": "test-original-token"},
        unique_id="test-email@test-domain.com",
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "menuai.components.melcloud.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-email@test-domain.com", "password": "test-password"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (TimeoutError(), "cannot_connect"),
        (AttributeError(name="get"), "invalid_auth"),
    ],
)
async def test_form_errors_reauthentication(
    menuai: menuai, mock_login, error, reason
) -> None:
    """Test we handle cannot connect error."""
    mock_login.side_effect = error
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test-email@test-domain.com", "token": "test-original-token"},
        unique_id="test-email@test-domain.com",
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reauth_flow(menuai)

    with patch(
        "menuai.components.melcloud.async_setup_entry",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-email@test-domain.com", "password": "test-password"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == reason

    mock_login.side_effect = None
    with patch(
        "menuai.components.melcloud.async_setup_entry",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-email@test-domain.com", "password": "test-password"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (HTTPStatus.UNAUTHORIZED, "invalid_auth"),
        (HTTPStatus.FORBIDDEN, "invalid_auth"),
        (HTTPStatus.INTERNAL_SERVER_ERROR, "cannot_connect"),
    ],
)
async def test_client_errors_reauthentication(
    menuai: menuai, mock_login, mock_request_info, error, reason
) -> None:
    """Test we handle cannot connect error."""
    mock_login.side_effect = ClientResponseError(mock_request_info(), (), status=error)
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test-email@test-domain.com", "token": "test-original-token"},
        unique_id="test-email@test-domain.com",
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reauth_flow(menuai)

    with patch(
        "menuai.components.melcloud.async_setup_entry",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-email@test-domain.com", "password": "test-password"},
        )
        await menuai.async_block_till_done()

    assert result["errors"]["base"] == reason
    assert result["type"] is FlowResultType.FORM

    mock_login.side_effect = None
    with patch(
        "menuai.components.melcloud.async_setup_entry",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-email@test-domain.com", "password": "test-password"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (HTTPStatus.UNAUTHORIZED, "invalid_auth"),
        (HTTPStatus.FORBIDDEN, "invalid_auth"),
        (HTTPStatus.INTERNAL_SERVER_ERROR, "cannot_connect"),
    ],
)
async def test_reconfigure_flow(
    menuai: menuai, mock_login, mock_request_info, error, reason
) -> None:
    """Test re-configuration flow."""
    mock_login.side_effect = ClientResponseError(mock_request_info(), (), status=error)
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test-email@test-domain.com", "token": "test-original-token"},
        unique_id="test-email@test-domain.com",
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reconfigure_flow(menuai)

    assert result["type"] is FlowResultType.FORM

    with patch(
        "menuai.components.melcloud.async_setup_entry",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PASSWORD: "test-password"},
        )
        await menuai.async_block_till_done()

    assert result["errors"]["base"] == reason
    assert result["type"] is FlowResultType.FORM

    mock_login.side_effect = None
    with patch(
        "menuai.components.melcloud.async_setup_entry",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PASSWORD: "test-password"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    entry = menuai.config_entries.async_get_entry(mock_entry.entry_id)
    assert entry
    assert entry.title == "Mock Title"
    assert entry.data == {
        "username": "test-email@test-domain.com",
        "token": "test-token",
        "password": "test-password",
    }


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (TimeoutError(), "cannot_connect"),
        (AttributeError(name="get"), "invalid_auth"),
    ],
)
async def test_form_errors_reconfigure(
    menuai: menuai, mock_login, error, reason
) -> None:
    """Test we handle cannot connect error."""
    mock_login.side_effect = error
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"username": "test-email@test-domain.com", "token": "test-original-token"},
        unique_id="test-email@test-domain.com",
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reconfigure_flow(menuai)

    with patch(
        "menuai.components.melcloud.async_setup_entry",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PASSWORD: "test-password"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == reason

    mock_login.side_effect = None
    with patch(
        "menuai.components.melcloud.async_setup_entry",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PASSWORD: "test-password"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    entry = menuai.config_entries.async_get_entry(mock_entry.entry_id)
    assert entry
    assert entry.title == "Mock Title"
    assert entry.data == {
        "username": "test-email@test-domain.com",
        "token": "test-token",
        "password": "test-password",
    }
