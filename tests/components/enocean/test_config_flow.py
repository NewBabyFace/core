"""Tests for EnOcean config flow."""

from unittest.mock import Mock, patch

from menuai import config_entries
from menuai.components.enocean.config_flow import EnOceanFlowHandler
from menuai.components.enocean.const import DOMAIN
from menuai.const import CONF_DEVICE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

DONGLE_VALIDATE_PATH_METHOD = "menuai.components.enocean.dongle.validate_path"
DONGLE_DETECT_METHOD = "menuai.components.enocean.dongle.detect"


async def test_user_flow_cannot_create_multiple_instances(menuai: menuai) -> None:
    """Test that the user flow aborts if an instance is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_DEVICE: "/already/configured/path"}
    )
    entry.add_to_menuai(menuai)

    with patch(DONGLE_VALIDATE_PATH_METHOD, Mock(return_value=True)):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_user_flow_with_detected_dongle(menuai: menuai) -> None:
    """Test the user flow with a detected EnOcean dongle."""
    FAKE_DONGLE_PATH = "/fake/dongle"

    with patch(DONGLE_DETECT_METHOD, Mock(return_value=[FAKE_DONGLE_PATH])):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "detect"
    devices = result["data_schema"].schema.get(CONF_DEVICE).config.get("options")
    assert FAKE_DONGLE_PATH in devices
    assert EnOceanFlowHandler.MANUAL_PATH_VALUE in devices


async def test_user_flow_with_no_detected_dongle(menuai: menuai) -> None:
    """Test the user flow with a detected EnOcean dongle."""
    with patch(DONGLE_DETECT_METHOD, Mock(return_value=[])):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"


async def test_detection_flow_with_valid_path(menuai: menuai) -> None:
    """Test the detection flow with a valid path selected."""
    USER_PROVIDED_PATH = "/user/provided/path"

    with patch(DONGLE_VALIDATE_PATH_METHOD, Mock(return_value=True)):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": "detect"}, data={CONF_DEVICE: USER_PROVIDED_PATH}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE] == USER_PROVIDED_PATH


async def test_detection_flow_with_custom_path(menuai: menuai) -> None:
    """Test the detection flow with custom path selected."""
    USER_PROVIDED_PATH = EnOceanFlowHandler.MANUAL_PATH_VALUE
    FAKE_DONGLE_PATH = "/fake/dongle"

    with (
        patch(DONGLE_VALIDATE_PATH_METHOD, Mock(return_value=True)),
        patch(DONGLE_DETECT_METHOD, Mock(return_value=[FAKE_DONGLE_PATH])),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "detect"},
            data={CONF_DEVICE: USER_PROVIDED_PATH},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"


async def test_detection_flow_with_invalid_path(menuai: menuai) -> None:
    """Test the detection flow with an invalid path selected."""
    USER_PROVIDED_PATH = "/invalid/path"
    FAKE_DONGLE_PATH = "/fake/dongle"

    with (
        patch(DONGLE_VALIDATE_PATH_METHOD, Mock(return_value=False)),
        patch(DONGLE_DETECT_METHOD, Mock(return_value=[FAKE_DONGLE_PATH])),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "detect"},
            data={CONF_DEVICE: USER_PROVIDED_PATH},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "detect"
    assert CONF_DEVICE in result["errors"]


async def test_manual_flow_with_valid_path(menuai: menuai) -> None:
    """Test the manual flow with a valid path."""
    USER_PROVIDED_PATH = "/user/provided/path"

    with patch(DONGLE_VALIDATE_PATH_METHOD, Mock(return_value=True)):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": "manual"}, data={CONF_DEVICE: USER_PROVIDED_PATH}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE] == USER_PROVIDED_PATH


async def test_manual_flow_with_invalid_path(menuai: menuai) -> None:
    """Test the manual flow with an invalid path."""
    USER_PROVIDED_PATH = "/user/provided/path"

    with patch(
        DONGLE_VALIDATE_PATH_METHOD,
        Mock(return_value=False),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": "manual"}, data={CONF_DEVICE: USER_PROVIDED_PATH}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    assert CONF_DEVICE in result["errors"]


async def test_import_flow_with_valid_path(menuai: menuai) -> None:
    """Test the import flow with a valid path."""
    DATA_TO_IMPORT = {CONF_DEVICE: "/valid/path/to/import"}

    with patch(DONGLE_VALIDATE_PATH_METHOD, Mock(return_value=True)):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=DATA_TO_IMPORT,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE] == DATA_TO_IMPORT[CONF_DEVICE]


async def test_import_flow_with_invalid_path(menuai: menuai) -> None:
    """Test the import flow with an invalid path."""
    DATA_TO_IMPORT = {CONF_DEVICE: "/invalid/path/to/import"}

    with patch(
        DONGLE_VALIDATE_PATH_METHOD,
        Mock(return_value=False),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=DATA_TO_IMPORT,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_dongle_path"
