"""Test the Foscam config flow."""

from unittest.mock import patch

from menuai import config_entries
from menuai.components.foscam import config_flow
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import setup_mock_foscam_camera
from .const import CAMERA_NAME, INVALID_RESPONSE_CONFIG, VALID_CONFIG

from tests.common import MockConfigEntry


async def test_user_valid(menuai: menuai) -> None:
    """Test valid config from user input."""

    result = await menuai.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.foscam.config_flow.FoscamCamera",
        ) as mock_foscam_camera,
        patch(
            "menuai.components.foscam.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        setup_mock_foscam_camera(mock_foscam_camera)

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_CONFIG,
        )

        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == CAMERA_NAME
        assert result["data"] == VALID_CONFIG

        assert len(mock_setup_entry.mock_calls) == 1


async def test_user_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth from user input."""

    result = await menuai.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.foscam.config_flow.FoscamCamera",
    ) as mock_foscam_camera:
        setup_mock_foscam_camera(mock_foscam_camera)

        invalid_user = VALID_CONFIG.copy()
        invalid_user[config_flow.CONF_USERNAME] = "invalid"

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            invalid_user,
        )

        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_user_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error from user input."""

    result = await menuai.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.foscam.config_flow.FoscamCamera",
    ) as mock_foscam_camera:
        setup_mock_foscam_camera(mock_foscam_camera)

        invalid_host = VALID_CONFIG.copy()
        invalid_host[config_flow.CONF_HOST] = "127.0.0.1"

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            invalid_host,
        )

        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_user_invalid_response(menuai: menuai) -> None:
    """Test we handle invalid response error from user input."""

    result = await menuai.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.foscam.config_flow.FoscamCamera",
    ) as mock_foscam_camera:
        setup_mock_foscam_camera(mock_foscam_camera)

        invalid_response = VALID_CONFIG.copy()
        invalid_response[config_flow.CONF_USERNAME] = INVALID_RESPONSE_CONFIG[
            config_flow.CONF_USERNAME
        ]

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            invalid_response,
        )

        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_response"}


async def test_user_already_configured(menuai: menuai) -> None:
    """Test we handle already configured from user input."""

    entry = MockConfigEntry(
        domain=config_flow.DOMAIN,
        data=VALID_CONFIG,
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.foscam.config_flow.FoscamCamera",
    ) as mock_foscam_camera:
        setup_mock_foscam_camera(mock_foscam_camera)

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_CONFIG,
        )

        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_user_unknown_exception(menuai: menuai) -> None:
    """Test we handle unknown exceptions from user input."""

    result = await menuai.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.foscam.config_flow.FoscamCamera",
    ) as mock_foscam_camera:
        mock_foscam_camera.side_effect = Exception("test")

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_CONFIG,
        )

        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}
