"""Tests for the iCloud config flow."""

from unittest.mock import MagicMock, Mock, patch

from pyicloud.exceptions import PyiCloudFailedLoginException
import pytest

from menuai.components.icloud.config_flow import (
    CONF_TRUSTED_DEVICE,
    CONF_VERIFICATION_CODE,
)
from menuai.components.icloud.const import (
    CONF_GPS_ACCURACY_THRESHOLD,
    CONF_MAX_INTERVAL,
    CONF_WITH_FAMILY,
    DEFAULT_GPS_ACCURACY_THRESHOLD,
    DEFAULT_MAX_INTERVAL,
    DEFAULT_WITH_FAMILY,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import (
    MOCK_CONFIG,
    PASSWORD,
    PASSWORD_2,
    TRUSTED_DEVICES,
    USERNAME,
    WITH_FAMILY,
)

from tests.common import MockConfigEntry


@pytest.fixture(name="icloud_bypass_setup", autouse=True)
def icloud_bypass_setup_fixture():
    """Mock component setup."""
    with patch("menuai.components.icloud.async_setup_entry", return_value=True):
        yield


@pytest.fixture(name="service")
def mock_controller_service():
    """Mock a successful service."""
    with patch(
        "menuai.components.icloud.config_flow.PyiCloudService"
    ) as service_mock:
        service_mock.return_value.requires_2fa = False
        service_mock.return_value.requires_2sa = True
        service_mock.return_value.trusted_devices = TRUSTED_DEVICES
        service_mock.return_value.send_verification_code = Mock(return_value=True)
        service_mock.return_value.validate_verification_code = Mock(return_value=True)
        yield service_mock


@pytest.fixture(name="service_2fa")
def mock_controller_2fa_service():
    """Mock a successful 2fa service."""
    with patch(
        "menuai.components.icloud.config_flow.PyiCloudService"
    ) as service_mock:
        service_mock.return_value.requires_2fa = True
        service_mock.return_value.requires_2sa = True
        service_mock.return_value.validate_2fa_code = Mock(return_value=True)
        service_mock.return_value.is_trusted_session = False
        yield service_mock


@pytest.fixture(name="service_authenticated")
def mock_controller_service_authenticated():
    """Mock a successful service while already authenticate."""
    with patch(
        "menuai.components.icloud.config_flow.PyiCloudService"
    ) as service_mock:
        service_mock.return_value.requires_2fa = False
        service_mock.return_value.requires_2sa = False
        service_mock.return_value.is_trusted_session = True
        service_mock.return_value.trusted_devices = TRUSTED_DEVICES
        service_mock.return_value.send_verification_code = Mock(return_value=True)
        service_mock.return_value.validate_2fa_code = Mock(return_value=True)
        service_mock.return_value.validate_verification_code = Mock(return_value=True)
        yield service_mock


@pytest.fixture(name="service_authenticated_no_device")
def mock_controller_service_authenticated_no_device():
    """Mock a successful service while already authenticate, but without device."""
    with patch(
        "menuai.components.icloud.config_flow.PyiCloudService"
    ) as service_mock:
        service_mock.return_value.requires_2fa = False
        service_mock.return_value.requires_2sa = False
        service_mock.return_value.trusted_devices = TRUSTED_DEVICES
        service_mock.return_value.send_verification_code = Mock(return_value=True)
        service_mock.return_value.validate_verification_code = Mock(return_value=True)
        service_mock.return_value.devices = {}
        yield service_mock


@pytest.fixture(name="service_authenticated_not_trusted")
def mock_controller_service_authenticated_not_trusted():
    """Mock a successful service while already authenticated, but the session is not trusted."""
    with patch(
        "menuai.components.icloud.config_flow.PyiCloudService"
    ) as service_mock:
        service_mock.return_value.requires_2fa = False
        service_mock.return_value.requires_2sa = False
        service_mock.return_value.is_trusted_session = False
        service_mock.return_value.trusted_devices = TRUSTED_DEVICES
        service_mock.return_value.send_verification_code = Mock(return_value=True)
        service_mock.return_value.validate_2fa_code = Mock(return_value=True)
        service_mock.return_value.validate_verification_code = Mock(return_value=True)
        yield service_mock


@pytest.fixture(name="service_send_verification_code_failed")
def mock_controller_service_send_verification_code_failed():
    """Mock a failed service during sending verification code step."""
    with patch(
        "menuai.components.icloud.config_flow.PyiCloudService"
    ) as service_mock:
        service_mock.return_value.requires_2fa = False
        service_mock.return_value.requires_2sa = True
        service_mock.return_value.trusted_devices = TRUSTED_DEVICES
        service_mock.return_value.send_verification_code = Mock(return_value=False)
        yield service_mock


@pytest.fixture(name="service_validate_2fa_code_failed")
def mock_controller_service_validate_2fa_code_failed():
    """Mock a failed service during validation of 2FA verification code step."""
    with patch(
        "menuai.components.icloud.config_flow.PyiCloudService"
    ) as service_mock:
        service_mock.return_value.requires_2fa = True
        service_mock.return_value.validate_2fa_code = Mock(return_value=False)
        yield service_mock


@pytest.fixture(name="service_validate_verification_code_failed")
def mock_controller_service_validate_verification_code_failed():
    """Mock a failed service during validation of verification code step."""
    with patch(
        "menuai.components.icloud.config_flow.PyiCloudService"
    ) as service_mock:
        service_mock.return_value.requires_2fa = False
        service_mock.return_value.requires_2sa = True
        service_mock.return_value.trusted_devices = TRUSTED_DEVICES
        service_mock.return_value.send_verification_code = Mock(return_value=True)
        service_mock.return_value.validate_verification_code = Mock(return_value=False)
        yield service_mock


async def test_user(menuai: menuai, service: MagicMock) -> None:
    """Test user config."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=None
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # test with required
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == CONF_TRUSTED_DEVICE


async def test_user_with_cookie(
    menuai: menuai, service_authenticated: MagicMock
) -> None:
    """Test user config with presence of a cookie."""
    # test with all provided
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
            CONF_WITH_FAMILY: WITH_FAMILY,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == USERNAME
    assert result["title"] == USERNAME
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD
    assert result["data"][CONF_WITH_FAMILY] == WITH_FAMILY
    assert result["data"][CONF_MAX_INTERVAL] == DEFAULT_MAX_INTERVAL
    assert result["data"][CONF_GPS_ACCURACY_THRESHOLD] == DEFAULT_GPS_ACCURACY_THRESHOLD


async def test_login_failed(menuai: menuai) -> None:
    """Test when we have errors during login."""
    with patch(
        "menuai.components.icloud.config_flow.PyiCloudService.authenticate",
        side_effect=PyiCloudFailedLoginException(),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {CONF_PASSWORD: "invalid_auth"}


async def test_no_device(
    menuai: menuai, service_authenticated_no_device: MagicMock
) -> None:
    """Test when we have no devices."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_device"


async def test_trusted_device(menuai: menuai, service: MagicMock) -> None:
    """Test trusted_device step."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == CONF_TRUSTED_DEVICE


async def test_trusted_device_success(menuai: menuai, service: MagicMock) -> None:
    """Test trusted_device step success."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TRUSTED_DEVICE: 0}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == CONF_VERIFICATION_CODE


async def test_send_verification_code_failed(
    menuai: menuai, service_send_verification_code_failed: MagicMock
) -> None:
    """Test when we have errors during send_verification_code."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TRUSTED_DEVICE: 0}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == CONF_TRUSTED_DEVICE
    assert result["errors"] == {CONF_TRUSTED_DEVICE: "send_verification_code"}


async def test_verification_code(menuai: menuai, service: MagicMock) -> None:
    """Test verification_code step."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TRUSTED_DEVICE: 0}
    )

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == CONF_VERIFICATION_CODE


async def test_verification_code_success(
    menuai: menuai, service: MagicMock
) -> None:
    """Test verification_code step success."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TRUSTED_DEVICE: 0}
    )
    service.return_value.requires_2sa = False

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_VERIFICATION_CODE: "0"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == USERNAME
    assert result["title"] == USERNAME
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD
    assert result["data"][CONF_WITH_FAMILY] == DEFAULT_WITH_FAMILY
    assert result["data"][CONF_MAX_INTERVAL] == DEFAULT_MAX_INTERVAL
    assert result["data"][CONF_GPS_ACCURACY_THRESHOLD] == DEFAULT_GPS_ACCURACY_THRESHOLD


async def test_validate_verification_code_failed(
    menuai: menuai, service_validate_verification_code_failed: MagicMock
) -> None:
    """Test when we have errors during validate_verification_code."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TRUSTED_DEVICE: 0}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_VERIFICATION_CODE: "0"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == CONF_TRUSTED_DEVICE
    assert result["errors"] == {"base": "validate_verification_code"}


async def test_2fa_code_success(menuai: menuai, service_2fa: MagicMock) -> None:
    """Test 2fa step success."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    service_2fa.return_value.requires_2fa = False
    service_2fa.return_value.requires_2sa = False

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_VERIFICATION_CODE: "0"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == USERNAME
    assert result["title"] == USERNAME
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD
    assert result["data"][CONF_WITH_FAMILY] == DEFAULT_WITH_FAMILY
    assert result["data"][CONF_MAX_INTERVAL] == DEFAULT_MAX_INTERVAL
    assert result["data"][CONF_GPS_ACCURACY_THRESHOLD] == DEFAULT_GPS_ACCURACY_THRESHOLD


async def test_validate_2fa_code_failed(
    menuai: menuai, service_validate_2fa_code_failed: MagicMock
) -> None:
    """Test when we have errors during validate_verification_code."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_VERIFICATION_CODE: "0"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == CONF_VERIFICATION_CODE
    assert result["errors"] == {"base": "validate_verification_code"}


async def test_password_update(
    menuai: menuai, service_authenticated: MagicMock
) -> None:
    """Test that password reauthentication works successfully."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, entry_id="test", unique_id=USERNAME
    )
    config_entry.add_to_menuai(menuai)

    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: PASSWORD_2}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PASSWORD] == PASSWORD_2


async def test_password_update_wrong_password(menuai: menuai) -> None:
    """Test that during password reauthentication wrong password returns correct error."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG, entry_id="test", unique_id=USERNAME
    )
    config_entry.add_to_menuai(menuai)

    result = await config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM

    with patch(
        "menuai.components.icloud.config_flow.PyiCloudService.authenticate",
        side_effect=PyiCloudFailedLoginException(),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: PASSWORD_2}
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {CONF_PASSWORD: "invalid_auth"}
