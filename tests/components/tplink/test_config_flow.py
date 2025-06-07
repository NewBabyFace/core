"""Test the tplink config flow."""

import logging
from unittest.mock import ANY, AsyncMock, patch

from kasa import Module, TimeoutError
import pytest

from menuai import config_entries
from menuai.components import stream
from menuai.components.tplink import (
    DOMAIN,
    AuthenticationError,
    Credentials,
    Device,
    DeviceConfig,
    KasaException,
)
from menuai.components.tplink.config_flow import TPLinkConfigFlow
from menuai.components.tplink.const import (
    CONF_CAMERA_CREDENTIALS,
    CONF_CONNECTION_PARAMETERS,
    CONF_CREDENTIALS_HASH,
    CONF_DEVICE_CONFIG,
    CONF_LIVE_VIEW,
)
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.const import (
    CONF_ALIAS,
    CONF_DEVICE,
    CONF_HOST,
    CONF_MAC,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.dhcp import DhcpServiceInfo

from . import _mocked_device, _patch_connect, _patch_discovery, _patch_single_discovery
from .conftest import override_side_effect
from .const import (
    AES_KEYS,
    ALIAS,
    ALIAS_CAMERA,
    CONN_PARAMS_AES,
    CONN_PARAMS_KLAP,
    CONN_PARAMS_LEGACY,
    CREATE_ENTRY_DATA_AES,
    CREATE_ENTRY_DATA_AES_CAMERA,
    CREATE_ENTRY_DATA_KLAP,
    CREATE_ENTRY_DATA_LEGACY,
    CREDENTIALS_HASH_AES,
    CREDENTIALS_HASH_KLAP,
    DEFAULT_ENTRY_TITLE,
    DEFAULT_ENTRY_TITLE_CAMERA,
    DEVICE_CONFIG_AES,
    DEVICE_CONFIG_AES_CAMERA,
    DEVICE_CONFIG_DICT_KLAP,
    DEVICE_CONFIG_KLAP,
    DEVICE_CONFIG_LEGACY,
    DHCP_FORMATTED_MAC_ADDRESS,
    IP_ADDRESS,
    IP_ADDRESS2,
    IP_ADDRESS3,
    MAC_ADDRESS,
    MAC_ADDRESS2,
    MAC_ADDRESS3,
    MODEL_CAMERA,
    MODULE,
    SMALLEST_VALID_JPEG_BYTES,
)

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("device_config", "expected_entry_data", "credentials_hash"),
    [
        pytest.param(
            DEVICE_CONFIG_KLAP, CREATE_ENTRY_DATA_KLAP, CREDENTIALS_HASH_KLAP, id="KLAP"
        ),
        pytest.param(
            DEVICE_CONFIG_AES, CREATE_ENTRY_DATA_AES, CREDENTIALS_HASH_AES, id="AES"
        ),
        pytest.param(DEVICE_CONFIG_LEGACY, CREATE_ENTRY_DATA_LEGACY, None, id="Legacy"),
    ],
)
async def test_discovery(
    menuai: menuai, device_config, expected_entry_data, credentials_hash
) -> None:
    """Test setting up discovery."""
    ip_address = device_config.host
    device = _mocked_device(
        device_config=device_config,
        credentials_hash=credentials_hash,
        ip_address=ip_address,
        mac=MAC_ADDRESS,
    )
    with (
        _patch_discovery(device, ip_address=ip_address),
        _patch_single_discovery(device),
        _patch_connect(device),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await menuai.async_block_till_done()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert not result["errors"]

        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()
        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "pick_device"
        assert not result2["errors"]

        # test we can try again
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert not result["errors"]

        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()
        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "pick_device"
        assert not result2["errors"]

    with (
        _patch_discovery(device, ip_address=ip_address),
        _patch_single_discovery(device),
        _patch_connect(device),
        patch(f"{MODULE}.async_setup", return_value=True) as mock_setup,
        patch(f"{MODULE}.async_setup_entry", return_value=True) as mock_setup_entry,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_DEVICE: MAC_ADDRESS},
        )
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == DEFAULT_ENTRY_TITLE
    assert result3["data"] == expected_entry_data
    mock_setup.assert_called_once()
    mock_setup_entry.assert_called_once()

    # ignore configured devices
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with _patch_discovery(), _patch_single_discovery(), _patch_connect():
        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "no_devices_found"


@pytest.mark.usefixtures("mock_init")
async def test_discovery_camera(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test authenticated discovery for camera with stream."""
    mock_device = _mocked_device(
        alias=ALIAS_CAMERA,
        ip_address=IP_ADDRESS3,
        mac=MAC_ADDRESS3,
        model=MODEL_CAMERA,
        device_config=DEVICE_CONFIG_AES_CAMERA,
        credentials_hash=CREDENTIALS_HASH_AES,
        modules=[Module.Camera],
    )

    with override_side_effect(mock_connect["connect"], lambda *_, **__: mock_device):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: IP_ADDRESS3,
                CONF_MAC: MAC_ADDRESS3,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: mock_device,
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    assert not result["errors"]

    with override_side_effect(mock_connect["connect"], lambda *_, **__: mock_device):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "camera_auth_confirm"
    assert not result["errors"]

    with patch(
        "menuai.components.stream.async_check_stream_client_error",
        return_value=None,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_LIVE_VIEW: True,
                CONF_USERNAME: "camuser",
                CONF_PASSWORD: "campass",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_ENTRY_TITLE_CAMERA
    assert result["data"] == CREATE_ENTRY_DATA_AES_CAMERA
    assert result["context"]["unique_id"] == MAC_ADDRESS3


@pytest.mark.usefixtures("mock_init")
async def test_discovery_pick_device_camera(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test authenticated discovery for camera with stream."""
    mock_device = _mocked_device(
        alias=ALIAS_CAMERA,
        ip_address=IP_ADDRESS3,
        mac=MAC_ADDRESS3,
        model=MODEL_CAMERA,
        device_config=DEVICE_CONFIG_AES_CAMERA,
        credentials_hash=CREDENTIALS_HASH_AES,
        modules=[Module.Camera],
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with override_side_effect(
        mock_discovery["discover"], lambda *_, **__: {IP_ADDRESS3: mock_device}
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "pick_device"
    assert not result["errors"]

    with override_side_effect(mock_connect["connect"], lambda *_, **__: mock_device):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_DEVICE: MAC_ADDRESS3},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "camera_auth_confirm"
    assert not result["errors"]

    with patch(
        "menuai.components.stream.async_check_stream_client_error",
        return_value=None,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_LIVE_VIEW: True,
                CONF_USERNAME: "camuser",
                CONF_PASSWORD: "campass",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_ENTRY_TITLE_CAMERA
    assert result["data"] == CREATE_ENTRY_DATA_AES_CAMERA
    assert result["context"]["unique_id"] == MAC_ADDRESS3


@pytest.mark.usefixtures("mock_init")
async def test_discovery_auth(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test authenticated discovery."""
    mock_device = _mocked_device(
        alias=ALIAS,
        ip_address=IP_ADDRESS,
        mac=MAC_ADDRESS,
        device_config=DEVICE_CONFIG_KLAP,
        credentials_hash=CREDENTIALS_HASH_KLAP,
    )

    with override_side_effect(mock_connect["connect"], AuthenticationError):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: IP_ADDRESS,
                CONF_MAC: MAC_ADDRESS,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: mock_device,
            },
        )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_auth_confirm"
    assert not result["errors"]

    with override_side_effect(mock_connect["connect"], lambda *_, **__: mock_device):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "fake_username",
                CONF_PASSWORD: "fake_password",
            },
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == DEFAULT_ENTRY_TITLE
    assert result2["data"] == CREATE_ENTRY_DATA_KLAP
    assert result2["context"]["unique_id"] == MAC_ADDRESS


@pytest.mark.usefixtures("mock_init")
async def test_discovery_auth_camera(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test authenticated discovery for camera with stream."""
    mock_device = _mocked_device(
        alias=ALIAS_CAMERA,
        ip_address=IP_ADDRESS3,
        mac=MAC_ADDRESS3,
        model=MODEL_CAMERA,
        device_config=DEVICE_CONFIG_AES_CAMERA,
        credentials_hash=CREDENTIALS_HASH_AES,
        modules=[Module.Camera],
    )

    with override_side_effect(mock_connect["connect"], AuthenticationError):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: IP_ADDRESS3,
                CONF_MAC: MAC_ADDRESS3,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: mock_device,
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_auth_confirm"
    assert not result["errors"]

    with override_side_effect(mock_connect["connect"], lambda *_, **__: mock_device):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "fake_username",
                CONF_PASSWORD: "fake_password",
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "camera_auth_confirm"
    assert not result["errors"]

    with patch(
        "menuai.components.stream.async_check_stream_client_error",
        return_value=None,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_LIVE_VIEW: True,
                CONF_USERNAME: "camuser",
                CONF_PASSWORD: "campass",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_ENTRY_TITLE_CAMERA
    assert result["data"] == CREATE_ENTRY_DATA_AES_CAMERA
    assert result["context"]["unique_id"] == MAC_ADDRESS3


@pytest.mark.parametrize(
    ("error_type", "errors_msg", "error_placement"),
    [
        (AuthenticationError("auth_error_details"), "invalid_auth", CONF_PASSWORD),
        (KasaException("smart_device_error_details"), "cannot_connect", "base"),
    ],
    ids=["invalid-auth", "unknown-error"],
)
@pytest.mark.usefixtures("mock_init")
async def test_discovery_auth_errors(
    menuai: menuai,
    mock_connect: AsyncMock,
    error_type: Exception,
    errors_msg: str,
    error_placement: str,
) -> None:
    """Test handling of discovery authentication errors.

    Tests for errors received during credential
    entry during discovery_auth_confirm.
    """
    mock_device = mock_connect["mock_devices"][IP_ADDRESS]

    with override_side_effect(mock_connect["connect"], AuthenticationError):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: IP_ADDRESS,
                CONF_MAC: MAC_ADDRESS,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: mock_device,
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_auth_confirm"
    assert not result["errors"]

    with override_side_effect(mock_connect["connect"], error_type):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "fake_username",
                CONF_PASSWORD: "fake_password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {error_placement: errors_msg}
    assert result2["description_placeholders"]["error"] == str(error_type)

    await menuai.async_block_till_done()

    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_USERNAME: "fake_username",
            CONF_PASSWORD: "fake_password",
        },
    )
    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["data"] == CREATE_ENTRY_DATA_KLAP
    assert result3["context"]["unique_id"] == MAC_ADDRESS


@pytest.mark.usefixtures("mock_init")
async def test_discovery_new_credentials(
    menuai: menuai,
    mock_connect: AsyncMock,
) -> None:
    """Test setting up discovery with new credentials."""
    mock_device = mock_connect["mock_devices"][IP_ADDRESS]

    with override_side_effect(mock_connect["connect"], AuthenticationError):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: IP_ADDRESS,
                CONF_MAC: MAC_ADDRESS,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: mock_device,
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_auth_confirm"
    assert not result["errors"]

    assert mock_connect["connect"].call_count == 1

    with patch(
        "menuai.components.tplink.config_flow.get_credentials",
        return_value=Credentials("fake_user", "fake_pass"),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
        )

    assert mock_connect["connect"].call_count == 2
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "discovery_confirm"

    await menuai.async_block_till_done()

    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        {},
    )
    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["data"] == CREATE_ENTRY_DATA_KLAP
    assert result3["context"]["unique_id"] == MAC_ADDRESS


@pytest.mark.usefixtures("mock_init")
async def test_discovery_new_credentials_invalid(
    menuai: menuai,
    mock_connect: AsyncMock,
) -> None:
    """Test setting up discovery with new invalid credentials."""
    mock_device = mock_connect["mock_devices"][IP_ADDRESS]

    with (
        patch("menuai.components.tplink.Discover.discover", return_value={}),
        patch(
            "menuai.components.tplink.config_flow.get_credentials",
            return_value=None,
        ),
        override_side_effect(mock_connect["connect"], AuthenticationError),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: IP_ADDRESS,
                CONF_MAC: MAC_ADDRESS,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: mock_device,
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_auth_confirm"
    assert not result["errors"]

    assert mock_connect["connect"].call_count == 1

    with (
        patch(
            "menuai.components.tplink.config_flow.get_credentials",
            return_value=Credentials("fake_user", "fake_pass"),
        ),
        override_side_effect(mock_connect["connect"], AuthenticationError),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
        )

    assert mock_connect["connect"].call_count == 2
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "discovery_auth_confirm"

    await menuai.async_block_till_done()

    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_USERNAME: "fake_username",
            CONF_PASSWORD: "fake_password",
        },
    )
    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["data"] == CREATE_ENTRY_DATA_KLAP
    assert result3["context"]["unique_id"] == MAC_ADDRESS


async def test_discovery_with_existing_device_present(menuai: menuai) -> None:
    """Test setting up discovery."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: IP_ADDRESS2}, unique_id="dd:dd:dd:dd:dd:dd"
    )
    config_entry.add_to_menuai(menuai)

    with (
        _patch_discovery(),
        _patch_single_discovery(no_device=True),
        _patch_connect(no_device=True),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with _patch_discovery(), _patch_single_discovery(), _patch_connect():
        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "pick_device"
    assert not result2["errors"]

    # Now abort and make sure we can start over

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with _patch_discovery(), _patch_single_discovery(), _patch_connect():
        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "pick_device"
    assert not result2["errors"]

    with (
        _patch_discovery(),
        _patch_single_discovery(),
        _patch_connect(),
        patch(f"{MODULE}.async_setup_entry", return_value=True) as mock_setup_entry,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_DEVICE: MAC_ADDRESS}
        )
        assert result3["type"] is FlowResultType.CREATE_ENTRY
        assert result3["title"] == DEFAULT_ENTRY_TITLE
        assert result3["data"] == CREATE_ENTRY_DATA_LEGACY
        assert result3["context"]["unique_id"] == MAC_ADDRESS
        await menuai.async_block_till_done()

    mock_setup_entry.assert_called_once()

    # ignore configured devices
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with _patch_discovery(), _patch_single_discovery(), _patch_connect():
        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "no_devices_found"


async def test_discovery_no_device(menuai: menuai) -> None:
    """Test discovery without device."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with _patch_discovery(no_device=True), _patch_single_discovery(), _patch_connect():
        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "no_devices_found"


async def test_manual(menuai: menuai) -> None:
    """Test manually setup."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    # Cannot connect (timeout)
    with (
        _patch_discovery(no_device=True),
        _patch_single_discovery(no_device=True),
        _patch_connect(no_device=True),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: IP_ADDRESS}
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "cannot_connect"}

    # Success
    with (
        _patch_discovery(),
        _patch_single_discovery(),
        _patch_connect(),
        patch(f"{MODULE}.async_setup", return_value=True),
        patch(f"{MODULE}.async_setup_entry", return_value=True),
    ):
        result4 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: IP_ADDRESS}
        )
        await menuai.async_block_till_done()
    assert result4["type"] is FlowResultType.CREATE_ENTRY
    assert result4["title"] == DEFAULT_ENTRY_TITLE
    assert result4["data"] == CREATE_ENTRY_DATA_LEGACY
    assert result4["context"]["unique_id"] == MAC_ADDRESS

    # Duplicate
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with (
        _patch_discovery(no_device=True),
        _patch_single_discovery(no_device=True),
        _patch_connect(no_device=True),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: IP_ADDRESS}
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_manual_camera(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test manual camera."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: IP_ADDRESS3}
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "camera_auth_confirm"

    # Test no username or pass
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIVE_VIEW: True,
            CONF_USERNAME: "camuser",
        },
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "camera_auth_confirm"
    assert result["errors"] == {"base": "camera_creds"}

    # Test unknown error
    with (
        patch(
            "menuai.components.stream.async_check_stream_client_error",
            side_effect=stream.StreamOpenClientError(
                "Stream was not found", error_code=stream.StreamClientError.NotFound
            ),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_LIVE_VIEW: True,
                CONF_USERNAME: "camuser",
                CONF_PASSWORD: "campass",
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "camera_auth_confirm"
    assert result["errors"] == {"base": "cannot_connect_camera"}
    assert "error" in result["description_placeholders"]

    # Test unknown error
    with (
        patch(
            "menuai.components.stream.async_check_stream_client_error",
            side_effect=stream.StreamOpenClientError(
                "Request is unauthorized",
                error_code=stream.StreamClientError.Unauthorized,
            ),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_LIVE_VIEW: True,
                CONF_USERNAME: "camuser",
                CONF_PASSWORD: "campass",
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "camera_auth_confirm"
    assert result["errors"] == {"base": "invalid_camera_auth"}

    with patch(
        "menuai.components.stream.async_check_stream_client_error",
        return_value=None,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_LIVE_VIEW: True,
                CONF_USERNAME: "camuser",
                CONF_PASSWORD: "campass",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CAMERA_CREDENTIALS] == {
        CONF_USERNAME: "camuser",
        CONF_PASSWORD: "campass",
    }
    assert result["data"][CONF_LIVE_VIEW] is True


@pytest.mark.parametrize(
    "exception",
    [
        pytest.param(
            stream.StreamOpenClientError(
                "Stream was not found", error_code=stream.StreamClientError.NotFound
            ),
            id="open_client_error",
        ),
        pytest.param(Exception(), id="other_error"),
    ],
)
async def test_manual_camera_no_hls(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
    exception: Exception,
) -> None:
    """Test manual camera when hls stream fails but mpeg stream works."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: IP_ADDRESS3}
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "camera_auth_confirm"

    # Test stream error
    with (
        patch(
            "menuai.components.stream.async_check_stream_client_error",
            side_effect=exception,
        ),
        patch("menuai.components.ffmpeg.async_get_image", return_value=None),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_LIVE_VIEW: True,
                CONF_USERNAME: "camuser",
                CONF_PASSWORD: "campass",
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "camera_auth_confirm"
    assert result["errors"] == {"base": "cannot_connect_camera"}
    assert "error" in result["description_placeholders"]

    # async_get_image will succeed
    with (
        patch(
            "menuai.components.stream.async_check_stream_client_error",
            side_effect=exception,
        ),
        patch(
            "menuai.components.ffmpeg.async_get_image",
            return_value=SMALLEST_VALID_JPEG_BYTES,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_LIVE_VIEW: True,
                CONF_USERNAME: "camuser",
                CONF_PASSWORD: "campass",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CAMERA_CREDENTIALS] == {
        CONF_USERNAME: "camuser",
        CONF_PASSWORD: "campass",
    }
    assert result["data"][CONF_LIVE_VIEW] is True


async def test_manual_camera_no_live_view(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test manual camera."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: IP_ADDRESS3}
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "camera_auth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_LIVE_VIEW: False,
            CONF_USERNAME: "camuser",
            CONF_PASSWORD: "campass",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert CONF_CAMERA_CREDENTIALS not in result["data"]
    assert result["data"][CONF_LIVE_VIEW] is False


async def test_manual_no_capabilities(menuai: menuai) -> None:
    """Test manually setup without successful get_capabilities."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with (
        _patch_discovery(no_device=True),
        _patch_single_discovery(),
        _patch_connect(),
        patch(f"{MODULE}.async_setup", return_value=True),
        patch(f"{MODULE}.async_setup_entry", return_value=True),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: IP_ADDRESS}
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == CREATE_ENTRY_DATA_LEGACY
    assert result["context"]["unique_id"] == MAC_ADDRESS


@pytest.mark.usefixtures("mock_init")
async def test_manual_auth(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test manually setup."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    mock_discovery["mock_devices"][IP_ADDRESS].update.side_effect = AuthenticationError

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: IP_ADDRESS}
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user_auth_confirm"
    assert not result2["errors"]

    mock_discovery["mock_devices"][IP_ADDRESS].update.reset_mock(side_effect=True)

    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={
            CONF_USERNAME: "fake_username",
            CONF_PASSWORD: "fake_password",
        },
    )
    await menuai.async_block_till_done()
    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == DEFAULT_ENTRY_TITLE
    assert result3["data"] == CREATE_ENTRY_DATA_KLAP
    assert result3["context"]["unique_id"] == MAC_ADDRESS


async def test_manual_auth_camera(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test manual camera."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with override_side_effect(
        mock_discovery["mock_devices"][IP_ADDRESS3].update, AuthenticationError
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: IP_ADDRESS3}
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user_auth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USERNAME: "foobar",
            CONF_PASSWORD: "foobar",
        },
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "camera_auth_confirm"

    with patch(
        "menuai.components.stream.async_check_stream_client_error",
        return_value=None,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_LIVE_VIEW: True,
                CONF_USERNAME: "camuser",
                CONF_PASSWORD: "campass",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CAMERA_CREDENTIALS] == {
        CONF_USERNAME: "camuser",
        CONF_PASSWORD: "campass",
    }
    assert result["data"][CONF_LIVE_VIEW] is True


@pytest.mark.parametrize(
    ("error_type", "errors_msg", "error_placement"),
    [
        (AuthenticationError("auth_error_details"), "invalid_auth", CONF_PASSWORD),
        (KasaException("smart_device_error_details"), "cannot_connect", "base"),
    ],
    ids=["invalid-auth", "unknown-error"],
)
@pytest.mark.usefixtures("mock_init")
async def test_manual_auth_errors(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
    error_type: Exception,
    errors_msg: str,
    error_placement: str,
) -> None:
    """Test manually setup auth errors."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    mock_discovery["mock_devices"][IP_ADDRESS].update.side_effect = AuthenticationError

    with override_side_effect(mock_connect["connect"], error_type):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_HOST: IP_ADDRESS}
        )
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user_auth_confirm"
    assert not result2["errors"]

    await menuai.async_block_till_done()
    with override_side_effect(mock_connect["connect"], error_type):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            user_input={
                CONF_USERNAME: "fake_username",
                CONF_PASSWORD: "fake_password",
            },
        )
        await menuai.async_block_till_done()
    assert result3["type"] is FlowResultType.FORM
    assert result3["step_id"] == "user_auth_confirm"
    assert result3["errors"] == {error_placement: errors_msg}
    assert result3["description_placeholders"]["error"] == str(error_type)

    result4 = await menuai.config_entries.flow.async_configure(
        result3["flow_id"],
        {
            CONF_USERNAME: "fake_username",
            CONF_PASSWORD: "fake_password",
        },
    )
    assert result4["type"] is FlowResultType.CREATE_ENTRY
    assert result4["data"] == CREATE_ENTRY_DATA_KLAP
    assert result4["context"]["unique_id"] == MAC_ADDRESS

    await menuai.async_block_till_done()


@pytest.mark.parametrize(
    ("host_str", "host", "port"),
    [
        (f"{IP_ADDRESS}:1234", IP_ADDRESS, 1234),
        ("[2001:db8:0::1]:4321", "2001:db8:0::1", 4321),
    ],
)
async def test_manual_port_override(
    menuai: menuai,
    mock_connect: AsyncMock,
    mock_discovery: AsyncMock,
    host_str: str,
    host: str,
    port: int,
) -> None:
    """Test manually setup."""
    config = DeviceConfig(
        host,
        credentials=None,
        port_override=port,
        connection_type=CONN_PARAMS_KLAP,
    )
    mock_device = _mocked_device(
        alias=ALIAS,
        ip_address=host,
        mac=MAC_ADDRESS,
        device_config=config,
        credentials_hash=CREDENTIALS_HASH_KLAP,
    )

    with override_side_effect(
        mock_discovery["try_connect_all"], lambda *_, **__: mock_device
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    # side_effects to cause auth confirm as the port override usually only
    # works with direct connections.
    mock_discovery["discover_single"].side_effect = TimeoutError
    mock_connect["connect"].side_effect = AuthenticationError

    with override_side_effect(
        mock_discovery["try_connect_all"], lambda *_, **__: mock_device
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: host_str}
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user_auth_confirm"
    assert not result2["errors"]

    creds = Credentials("fake_username", "fake_password")
    with override_side_effect(
        mock_discovery["try_connect_all"], lambda *_, **__: mock_device
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            user_input={
                CONF_USERNAME: "fake_username",
                CONF_PASSWORD: "fake_password",
            },
        )
    await menuai.async_block_till_done()
    mock_discovery["try_connect_all"].assert_called_once_with(
        host, credentials=creds, port=port, http_client=ANY
    )
    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == DEFAULT_ENTRY_TITLE
    assert result3["data"] == {
        **CREATE_ENTRY_DATA_KLAP,
        CONF_PORT: port,
        CONF_HOST: host,
    }
    assert result3["context"]["unique_id"] == MAC_ADDRESS


async def test_manual_port_override_invalid(
    menuai: menuai, mock_connect: AsyncMock, mock_discovery: AsyncMock
) -> None:
    """Test manually setup."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: f"{IP_ADDRESS}:foo"}
    )
    await menuai.async_block_till_done()

    mock_discovery["discover_single"].assert_called_once_with(
        IP_ADDRESS, credentials=None, port=None
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == DEFAULT_ENTRY_TITLE
    assert result2["data"] == CREATE_ENTRY_DATA_KLAP
    assert result2["context"]["unique_id"] == MAC_ADDRESS


async def test_discovered_by_discovery_and_dhcp(menuai: menuai) -> None:
    """Test we get the form with discovery and abort for dhcp source when we get both."""

    with _patch_discovery(), _patch_single_discovery(), _patch_connect():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: IP_ADDRESS,
                CONF_MAC: MAC_ADDRESS,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: _mocked_device(device_config=DEVICE_CONFIG_LEGACY),
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    real_is_matching = TPLinkConfigFlow.is_matching
    return_values = []

    def is_matching(self, other_flow) -> bool:
        return_values.append(real_is_matching(self, other_flow))
        return return_values[-1]

    with (
        _patch_discovery(),
        _patch_single_discovery(),
        _patch_connect(),
        patch.object(TPLinkConfigFlow, "is_matching", wraps=is_matching, autospec=True),
    ):
        result2 = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(
                ip=IP_ADDRESS, macaddress=DHCP_FORMATTED_MAC_ADDRESS, hostname=ALIAS
            ),
        )
        await menuai.async_block_till_done()
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_in_progress"
    # Ensure the is_matching method returned True
    assert return_values == [True]

    with _patch_discovery(), _patch_single_discovery(), _patch_connect():
        result3 = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(
                ip=IP_ADDRESS, macaddress="000000000000", hostname="mock_hostname"
            ),
        )
        await menuai.async_block_till_done()
    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "already_in_progress"

    with (
        _patch_discovery(no_device=True),
        _patch_single_discovery(no_device=True),
        _patch_connect(no_device=True),
    ):
        result3 = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(
                ip="1.2.3.5", macaddress="000000000001", hostname="mock_hostname"
            ),
        )
        await menuai.async_block_till_done()
    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "cannot_connect"


@pytest.mark.parametrize(
    ("source", "data"),
    [
        (
            config_entries.SOURCE_DHCP,
            DhcpServiceInfo(
                ip=IP_ADDRESS, macaddress=DHCP_FORMATTED_MAC_ADDRESS, hostname=ALIAS
            ),
        ),
        (
            config_entries.SOURCE_INTEGRATION_DISCOVERY,
            {
                CONF_HOST: IP_ADDRESS,
                CONF_MAC: MAC_ADDRESS,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: _mocked_device(device_config=DEVICE_CONFIG_LEGACY),
            },
        ),
    ],
)
async def test_discovered_by_dhcp_or_discovery(
    menuai: menuai, source: str, data: dict
) -> None:
    """Test we can setup when discovered from dhcp or discovery."""

    with _patch_discovery(), _patch_single_discovery(), _patch_connect():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": source}, data=data
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        _patch_discovery(),
        _patch_single_discovery(),
        _patch_connect(),
        patch(f"{MODULE}.async_setup", return_value=True) as mock_async_setup,
        patch(
            f"{MODULE}.async_setup_entry", return_value=True
        ) as mock_async_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == CREATE_ENTRY_DATA_LEGACY
    assert result2["context"]["unique_id"] == MAC_ADDRESS

    assert mock_async_setup.called
    assert mock_async_setup_entry.called


@pytest.mark.parametrize(
    ("source", "data"),
    [
        (
            config_entries.SOURCE_DHCP,
            DhcpServiceInfo(
                ip=IP_ADDRESS, macaddress=DHCP_FORMATTED_MAC_ADDRESS, hostname=ALIAS
            ),
        ),
        (
            config_entries.SOURCE_INTEGRATION_DISCOVERY,
            {
                CONF_HOST: IP_ADDRESS,
                CONF_MAC: MAC_ADDRESS,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: _mocked_device(device_config=DEVICE_CONFIG_LEGACY),
            },
        ),
    ],
)
async def test_discovered_by_dhcp_or_discovery_failed_to_get_device(
    menuai: menuai, source: str, data: dict
) -> None:
    """Test we abort if we cannot get the unique id when discovered from dhcp."""

    with (
        _patch_discovery(no_device=True),
        _patch_single_discovery(no_device=True),
        _patch_connect(no_device=True),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": source}, data=data
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_integration_discovery_with_ip_change(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test integration updates ip address from discovery."""
    mock_config_entry.add_to_menuai(menuai)
    with (
        patch("menuai.components.tplink.Discover.discover", return_value={}),
        override_side_effect(mock_connect["connect"], KasaException()),
    ):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 0
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS]
        == CONN_PARAMS_LEGACY.to_dict()
    )
    assert mock_config_entry.data[CONF_HOST] == IP_ADDRESS

    mocked_device = _mocked_device(device_config=DEVICE_CONFIG_KLAP)
    with override_side_effect(mock_connect["connect"], lambda *_, **__: mocked_device):
        discovery_result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: IP_ADDRESS2,
                CONF_MAC: MAC_ADDRESS,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: mocked_device,
            },
        )
    await menuai.async_block_till_done()
    assert discovery_result["type"] is FlowResultType.ABORT
    assert discovery_result["reason"] == "already_configured"
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS] == CONN_PARAMS_KLAP.to_dict()
    )
    assert mock_config_entry.data[CONF_HOST] == IP_ADDRESS2

    config = DeviceConfig.from_dict(DEVICE_CONFIG_DICT_KLAP)

    # Do a reload here and check that the
    # new config is picked up in setup_entry
    mock_connect["connect"].reset_mock(side_effect=True)
    bulb = _mocked_device(
        device_config=config,
        mac=mock_config_entry.unique_id,
    )

    with (
        patch(
            "menuai.components.tplink.async_create_clientsession",
            return_value="Foo",
        ),
        override_side_effect(mock_connect["connect"], lambda *_, **__: bulb),
    ):
        await menuai.config_entries.async_reload(mock_config_entry.entry_id)
        await menuai.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    # Check that init set the new host correctly before calling connect
    assert config.host == IP_ADDRESS
    config.host = IP_ADDRESS2
    config.http_client = "Foo"
    mock_connect["connect"].assert_awaited_once_with(config=config)


async def test_integration_discovery_with_connection_change(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test that config entry is updated with new device config.

    And that connection_hash is removed as it will be invalid.
    """
    mock_config_entry = MockConfigEntry(
        title="TPLink",
        domain=DOMAIN,
        data=CREATE_ENTRY_DATA_AES,
        unique_id=MAC_ADDRESS2,
    )
    mock_config_entry.add_to_menuai(menuai)
    with (
        patch("menuai.components.tplink.Discover.discover", return_value={}),
        override_side_effect(mock_connect["connect"], KasaException()),
    ):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done(wait_background_tasks=True)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
    assert (
        len(
            menuai.config_entries.flow.async_progress_by_handler(
                DOMAIN, match_context={"source": SOURCE_REAUTH}
            )
        )
        == 0
    )
    assert mock_config_entry.data[CONF_HOST] == IP_ADDRESS2
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS] == CONN_PARAMS_AES.to_dict()
    )
    assert mock_config_entry.data[CONF_CREDENTIALS_HASH] == CREDENTIALS_HASH_AES

    mock_connect["connect"].reset_mock()
    NEW_DEVICE_CONFIG = {
        **DEVICE_CONFIG_DICT_KLAP,
        "connection_type": CONN_PARAMS_KLAP.to_dict(),
        CONF_HOST: IP_ADDRESS2,
    }
    config = DeviceConfig.from_dict(NEW_DEVICE_CONFIG)
    # Reset the connect mock so when the config flow reloads the entry it succeeds

    bulb = _mocked_device(
        device_config=config,
        mac=mock_config_entry.unique_id,
    )

    with (
        patch(
            "menuai.components.tplink.async_create_clientsession",
            return_value="Foo",
        ),
        override_side_effect(mock_connect["connect"], lambda *_, **__: bulb),
    ):
        discovery_result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: IP_ADDRESS2,
                CONF_MAC: MAC_ADDRESS2,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: bulb,
            },
        )
    await menuai.async_block_till_done(wait_background_tasks=True)
    assert discovery_result["type"] is FlowResultType.ABORT
    assert discovery_result["reason"] == "already_configured"
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS] == CONN_PARAMS_KLAP.to_dict()
    )
    assert mock_config_entry.data[CONF_HOST] == IP_ADDRESS2
    assert CREDENTIALS_HASH_AES not in mock_config_entry.data

    assert mock_config_entry.state is ConfigEntryState.LOADED

    config.host = IP_ADDRESS2
    config.http_client = "Foo"
    config.aes_keys = AES_KEYS
    mock_connect["connect"].assert_awaited_once_with(config=config)


async def test_dhcp_discovery_with_ip_change(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test dhcp discovery with an IP change."""
    mock_config_entry.add_to_menuai(menuai)
    with (
        patch("menuai.components.tplink.Discover.discover", return_value={}),
        override_side_effect(mock_connect["connect"], KasaException()),
    ):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 0
    assert mock_config_entry.data[CONF_HOST] == IP_ADDRESS

    discovery_result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data=DhcpServiceInfo(
            ip=IP_ADDRESS2, macaddress=DHCP_FORMATTED_MAC_ADDRESS, hostname=ALIAS
        ),
    )
    assert discovery_result["type"] is FlowResultType.ABORT
    assert discovery_result["reason"] == "already_configured"
    assert mock_config_entry.data[CONF_HOST] == IP_ADDRESS2


async def test_dhcp_discovery_discover_fail(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test dhcp discovery source cannot discover_single."""

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 0
    assert mock_config_entry.data[CONF_HOST] == IP_ADDRESS

    with override_side_effect(mock_discovery["discover_single"], TimeoutError):
        discovery_result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(
                ip=IP_ADDRESS2, macaddress=DHCP_FORMATTED_MAC_ADDRESS, hostname=ALIAS
            ),
        )
    assert discovery_result["type"] is FlowResultType.ABORT
    assert discovery_result["reason"] == "cannot_connect"


async def test_reauth(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test reauth flow."""
    mock_added_config_entry.async_start_reauth(menuai)
    await menuai.async_block_till_done()

    assert mock_added_config_entry.state is ConfigEntryState.LOADED
    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    [result] = flows
    assert result["step_id"] == "reauth_confirm"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USERNAME: "fake_username",
            CONF_PASSWORD: "fake_password",
        },
    )
    credentials = Credentials("fake_username", "fake_password")
    mock_discovery["discover_single"].assert_called_once_with(
        IP_ADDRESS, credentials=credentials, port=None
    )
    mock_discovery["mock_devices"][IP_ADDRESS].update.assert_called_once_with()
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"

    await menuai.async_block_till_done()


async def test_reauth_camera(
    menuai: menuai,
    mock_camera_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test reauth flow on invalid camera credentials."""
    mock_device = mock_connect["mock_devices"][IP_ADDRESS3]
    mock_camera_config_entry.add_to_menuai(menuai)
    mock_camera_config_entry.async_start_reauth(
        menuai,
        config_entries.ConfigFlowContext(
            reauth_source=CONF_CAMERA_CREDENTIALS,  # type: ignore[typeddict-unknown-key]
        ),
        {"device": mock_device},
    )
    await menuai.async_block_till_done()
    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    [result] = flows

    assert result["step_id"] == "camera_auth_confirm"

    with patch(
        "menuai.components.stream.async_check_stream_client_error",
        return_value=None,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_LIVE_VIEW: True,
                CONF_USERNAME: "camuser2",
                CONF_PASSWORD: "campass2",
            },
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert dict(mock_camera_config_entry.data) == {
        **CREATE_ENTRY_DATA_AES_CAMERA,
        CONF_CAMERA_CREDENTIALS: {CONF_USERNAME: "camuser2", CONF_PASSWORD: "campass2"},
    }


async def test_reauth_try_connect_all(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test reauth flow."""
    mock_added_config_entry.async_start_reauth(menuai)
    await menuai.async_block_till_done()

    assert mock_added_config_entry.state is ConfigEntryState.LOADED
    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    [result] = flows
    assert result["step_id"] == "reauth_confirm"

    with override_side_effect(mock_discovery["discover_single"], TimeoutError):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "fake_username",
                CONF_PASSWORD: "fake_password",
            },
        )
    credentials = Credentials("fake_username", "fake_password")
    mock_discovery["discover_single"].assert_called_once_with(
        IP_ADDRESS, credentials=credentials, port=None
    )
    mock_discovery["try_connect_all"].assert_called_once()
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"

    await menuai.async_block_till_done()


async def test_reauth_try_connect_all_fail(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test reauth flow."""
    mock_added_config_entry.async_start_reauth(menuai)
    await menuai.async_block_till_done()

    assert mock_added_config_entry.state is ConfigEntryState.LOADED
    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    [result] = flows
    assert result["step_id"] == "reauth_confirm"

    with (
        override_side_effect(mock_discovery["discover_single"], TimeoutError),
        override_side_effect(mock_discovery["try_connect_all"], lambda *_, **__: None),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "fake_username",
                CONF_PASSWORD: "fake_password",
            },
        )
    credentials = Credentials("fake_username", "fake_password")
    mock_discovery["discover_single"].assert_called_once_with(
        IP_ADDRESS, credentials=credentials, port=None
    )
    mock_discovery["try_connect_all"].assert_called_once()
    assert result["errors"] == {"base": "cannot_connect"}

    mock_discovery["try_connect_all"].reset_mock()
    with (
        override_side_effect(mock_discovery["discover_single"], TimeoutError),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "fake_username",
                CONF_PASSWORD: "fake_password",
            },
        )

    mock_discovery["try_connect_all"].assert_called_once()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_reauth_update_with_encryption_change(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test reauth flow."""

    mock_config_entry = MockConfigEntry(
        title="TPLink",
        domain=DOMAIN,
        data={**CREATE_ENTRY_DATA_AES},
        unique_id=MAC_ADDRESS2,
    )
    mock_config_entry.add_to_menuai(menuai)
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS] == CONN_PARAMS_AES.to_dict()
    )
    assert mock_config_entry.data[CONF_CREDENTIALS_HASH] == CREDENTIALS_HASH_AES

    with (
        patch("menuai.components.tplink.Discover.discover", return_value={}),
        override_side_effect(mock_connect["connect"], AuthenticationError()),
    ):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR

    caplog.set_level(logging.DEBUG)
    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    [result] = flows
    assert result["step_id"] == "reauth_confirm"
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS] == CONN_PARAMS_AES.to_dict()
    )
    assert CONF_CREDENTIALS_HASH not in mock_config_entry.data

    new_config = DeviceConfig(
        IP_ADDRESS2,
        credentials=None,
        connection_type=Device.ConnectionParameters(
            Device.Family.SmartTapoPlug, Device.EncryptionType.Klap
        ),
    )
    mock_device = _mocked_device(
        alias="my_device",
        ip_address=IP_ADDRESS2,
        mac=MAC_ADDRESS2,
        device_config=new_config,
        credentials_hash=CREDENTIALS_HASH_KLAP,
    )

    with (
        override_side_effect(
            mock_discovery["discover_single"], lambda *_, **__: mock_device
        ),
        override_side_effect(mock_connect["connect"], lambda *_, **__: mock_device),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "fake_username",
                CONF_PASSWORD: "fake_password",
            },
        )
        await menuai.async_block_till_done(wait_background_tasks=True)
    assert "Connection type changed for 127.0.0.2" in caplog.text
    credentials = Credentials("fake_username", "fake_password")
    mock_discovery["discover_single"].assert_called_once_with(
        IP_ADDRESS2, credentials=credentials, port=None
    )
    mock_device.update.assert_called_once_with()
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS] == CONN_PARAMS_KLAP.to_dict()
    )
    assert mock_config_entry.data[CONF_HOST] == IP_ADDRESS2
    assert mock_config_entry.data[CONF_CREDENTIALS_HASH] == CREDENTIALS_HASH_KLAP


async def test_reauth_update_from_discovery(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test reauth flow."""
    mock_config_entry.add_to_menuai(menuai)
    with (
        patch("menuai.components.tplink.Discover.discover", return_value={}),
        override_side_effect(mock_connect["connect"], AuthenticationError()),
    ):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    [result] = flows
    assert result["step_id"] == "reauth_confirm"
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS]
        == CONN_PARAMS_LEGACY.to_dict()
    )

    device = _mocked_device(
        device_config=DEVICE_CONFIG_KLAP,
        mac=mock_config_entry.unique_id,
    )
    with override_side_effect(mock_connect["connect"], lambda *_, **__: device):
        discovery_result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: IP_ADDRESS,
                CONF_MAC: MAC_ADDRESS,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: device,
            },
        )
    await menuai.async_block_till_done()
    assert discovery_result["type"] is FlowResultType.ABORT
    assert discovery_result["reason"] == "already_configured"
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS] == CONN_PARAMS_KLAP.to_dict()
    )


async def test_reauth_update_from_discovery_with_ip_change(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test reauth flow."""
    mock_config_entry.add_to_menuai(menuai)
    with (
        patch("menuai.components.tplink.Discover.discover", return_value={}),
        override_side_effect(mock_connect["connect"], AuthenticationError()),
    ):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    [result] = flows
    assert result["step_id"] == "reauth_confirm"
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS]
        == CONN_PARAMS_LEGACY.to_dict()
    )

    device = _mocked_device(
        device_config=DEVICE_CONFIG_KLAP,
        mac=mock_config_entry.unique_id,
    )
    with override_side_effect(mock_connect["connect"], lambda *_, **__: device):
        discovery_result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: IP_ADDRESS2,
                CONF_MAC: MAC_ADDRESS,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: device,
            },
        )
    await menuai.async_block_till_done()
    assert discovery_result["type"] is FlowResultType.ABORT
    assert discovery_result["reason"] == "already_configured"
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS] == CONN_PARAMS_KLAP.to_dict()
    )
    assert mock_config_entry.data[CONF_HOST] == IP_ADDRESS2


async def test_reauth_no_update_if_config_and_ip_the_same(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test reauth discovery does not update when the host and config are the same."""
    mock_config_entry.add_to_menuai(menuai)

    menuai.config_entries.async_update_entry(
        mock_config_entry,
        data={
            **mock_config_entry.data,
            CONF_DEVICE_CONFIG: DEVICE_CONFIG_DICT_KLAP,
        },
    )
    with override_side_effect(mock_connect["connect"], AuthenticationError()):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    [result] = flows
    assert result["step_id"] == "reauth_confirm"
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS] == CONN_PARAMS_KLAP.to_dict()
    )

    device = _mocked_device(
        device_config=DEVICE_CONFIG_KLAP,
        mac=mock_config_entry.unique_id,
    )
    with override_side_effect(mock_connect["connect"], lambda *_, **__: device):
        discovery_result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: IP_ADDRESS,
                CONF_MAC: MAC_ADDRESS,
                CONF_ALIAS: ALIAS,
                CONF_DEVICE: device,
            },
        )
    await menuai.async_block_till_done()
    assert discovery_result["type"] is FlowResultType.ABORT
    assert discovery_result["reason"] == "already_configured"
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS] == CONN_PARAMS_KLAP.to_dict()
    )
    assert mock_config_entry.data[CONF_HOST] == IP_ADDRESS


@pytest.mark.parametrize(
    ("error_type", "errors_msg", "error_placement"),
    [
        (AuthenticationError("auth_error_details"), "invalid_auth", CONF_PASSWORD),
        (KasaException("smart_device_error_details"), "cannot_connect", "base"),
    ],
    ids=["invalid-auth", "unknown-error"],
)
async def test_reauth_errors(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
    error_type: Exception,
    errors_msg: str,
    error_placement: str,
) -> None:
    """Test reauth errors."""
    mock_added_config_entry.async_start_reauth(menuai)
    await menuai.async_block_till_done()

    assert mock_added_config_entry.state is ConfigEntryState.LOADED
    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    [result] = flows
    assert result["step_id"] == "reauth_confirm"

    mock_device = mock_discovery["mock_devices"][IP_ADDRESS]
    with override_side_effect(mock_device.update, error_type):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_USERNAME: "fake_username",
                CONF_PASSWORD: "fake_password",
            },
        )
    credentials = Credentials("fake_username", "fake_password")

    mock_discovery["discover_single"].assert_called_once_with(
        IP_ADDRESS, credentials=credentials, port=None
    )
    mock_device.update.assert_called_once_with()
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {error_placement: errors_msg}
    assert result2["description_placeholders"]["error"] == str(error_type)

    mock_discovery["discover_single"].reset_mock()
    mock_device.update.reset_mock(side_effect=True)
    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={
            CONF_USERNAME: "fake_username",
            CONF_PASSWORD: "fake_password",
        },
    )

    mock_discovery["discover_single"].assert_called_once_with(
        IP_ADDRESS, credentials=credentials, port=None
    )
    mock_device.update.assert_called_once_with()

    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "reauth_successful"


@pytest.mark.parametrize(
    ("error_type", "expected_flow"),
    [
        (AuthenticationError, FlowResultType.FORM),
        (KasaException, FlowResultType.ABORT),
    ],
    ids=["invalid-auth", "unknown-error"],
)
async def test_pick_device_errors(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
    error_type: type[Exception],
    expected_flow: FlowResultType,
) -> None:
    """Test errors on pick_device."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    await menuai.async_block_till_done()
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "pick_device"
    assert not result2["errors"]

    with override_side_effect(mock_connect["connect"], error_type):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            {CONF_DEVICE: MAC_ADDRESS},
        )
        await menuai.async_block_till_done()
    assert result3["type"] == expected_flow

    if expected_flow != FlowResultType.ABORT:
        result4 = await menuai.config_entries.flow.async_configure(
            result3["flow_id"],
            user_input={
                CONF_USERNAME: "fake_username",
                CONF_PASSWORD: "fake_password",
            },
        )
        assert result4["type"] is FlowResultType.CREATE_ENTRY
        assert result4["context"]["unique_id"] == MAC_ADDRESS


@pytest.mark.usefixtures("mock_init")
async def test_discovery_timeout_try_connect_all(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test discovery tries legacy connect on timeout."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    mock_discovery["discover_single"].side_effect = TimeoutError
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]
    assert mock_connect["connect"].call_count == 0

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: IP_ADDRESS}
    )
    await menuai.async_block_till_done()
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["context"]["unique_id"] == MAC_ADDRESS
    assert mock_connect["connect"].call_count == 1


@pytest.mark.usefixtures("mock_init")
async def test_discovery_timeout_try_connect_all_needs_creds(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test discovery tries legacy connect on timeout."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    mock_discovery["discover_single"].side_effect = TimeoutError
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]
    assert mock_connect["connect"].call_count == 0

    with override_side_effect(mock_connect["connect"], KasaException):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: IP_ADDRESS}
        )
        await menuai.async_block_till_done()
    assert result2["step_id"] == "user_auth_confirm"
    assert result2["type"] is FlowResultType.FORM

    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={
            CONF_USERNAME: "fake_username",
            CONF_PASSWORD: "fake_password",
        },
    )
    await menuai.async_block_till_done()
    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["context"]["unique_id"] == MAC_ADDRESS
    assert mock_connect["connect"].call_count == 1


@pytest.mark.usefixtures("mock_init")
async def test_discovery_timeout_try_connect_all_fail(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test discovery tries legacy connect on timeout."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    mock_discovery["discover_single"].side_effect = TimeoutError
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]
    assert mock_connect["connect"].call_count == 0

    with override_side_effect(mock_connect["connect"], KasaException):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: IP_ADDRESS}
        )
        await menuai.async_block_till_done()
    assert result2["step_id"] == "user_auth_confirm"
    assert result2["type"] is FlowResultType.FORM

    with override_side_effect(mock_discovery["try_connect_all"], lambda *_, **__: None):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            user_input={
                CONF_USERNAME: "fake_username",
                CONF_PASSWORD: "fake_password",
            },
        )
        await menuai.async_block_till_done()
    assert result3["errors"] == {"base": "cannot_connect"}
    assert mock_connect["connect"].call_count == 1


async def test_reauth_update_other_flows(
    menuai: menuai,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test reauth updates other reauth flows."""
    mock_config_entry = MockConfigEntry(
        title="TPLink",
        domain=DOMAIN,
        data={**CREATE_ENTRY_DATA_KLAP},
        unique_id=MAC_ADDRESS,
    )
    mock_config_entry2 = MockConfigEntry(
        title="TPLink",
        domain=DOMAIN,
        data={**CREATE_ENTRY_DATA_AES},
        unique_id=MAC_ADDRESS2,
    )
    mock_config_entry.add_to_menuai(menuai)
    mock_config_entry2.add_to_menuai(menuai)
    with (
        patch("menuai.components.tplink.Discover.discover", return_value={}),
        override_side_effect(mock_connect["connect"], AuthenticationError()),
    ):
        await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

    assert mock_config_entry2.state is ConfigEntryState.SETUP_ERROR
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR

    await menuai.async_block_till_done()

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 2
    flows_by_entry_id = {flow["context"]["entry_id"]: flow for flow in flows}
    result = flows_by_entry_id[mock_config_entry.entry_id]
    assert result["step_id"] == "reauth_confirm"
    assert (
        mock_config_entry.data[CONF_CONNECTION_PARAMETERS] == CONN_PARAMS_KLAP.to_dict()
    )
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USERNAME: "fake_username",
            CONF_PASSWORD: "fake_password",
        },
    )
    credentials = Credentials("fake_username", "fake_password")
    mock_discovery["discover_single"].assert_called_once_with(
        IP_ADDRESS, credentials=credentials, port=None
    )
    mock_discovery["mock_devices"][IP_ADDRESS].update.assert_called_once_with()
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"

    await menuai.async_block_till_done()
    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 0


async def test_reconfigure(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test reconfigure flow."""
    result = await mock_added_config_entry.start_reconfigure_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: IP_ADDRESS,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_reconfigure_auth_discovered(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test reconfigure auth flow for device that's discovered."""
    result = await mock_added_config_entry.start_reconfigure_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    # Simulate a bad host
    with (
        override_side_effect(
            mock_discovery["mock_devices"][IP_ADDRESS].update, KasaException
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "WRONG_IP",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "cannot_connect"}
    assert "error" in result["description_placeholders"]

    with (
        override_side_effect(
            mock_discovery["mock_devices"][IP_ADDRESS].update, AuthenticationError
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: IP_ADDRESS,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user_auth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USERNAME: "user",
            CONF_PASSWORD: "pass",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_reconfigure_auth_try_connect_all(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test reconfigure auth flow for device that's not discovered."""
    result = await mock_added_config_entry.start_reconfigure_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with (
        override_side_effect(mock_discovery["discover_single"], TimeoutError),
        override_side_effect(mock_connect["connect"], KasaException),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: IP_ADDRESS,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user_auth_confirm"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USERNAME: "user",
            CONF_PASSWORD: "pass",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_reconfigure_camera(
    menuai: menuai,
    mock_camera_config_entry: MockConfigEntry,
    mock_discovery: AsyncMock,
    mock_connect: AsyncMock,
) -> None:
    """Test reconfigure flow."""
    mock_camera_config_entry.add_to_menuai(menuai)
    result = await mock_camera_config_entry.start_reconfigure_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: IP_ADDRESS3,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "camera_auth_confirm"

    with patch(
        "menuai.components.stream.async_check_stream_client_error",
        return_value=None,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_LIVE_VIEW: True,
                CONF_USERNAME: "camuser",
                CONF_PASSWORD: "campass",
            },
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
