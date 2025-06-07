"""Test the Trafikverket Camera config flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytrafikverket import (
    CameraInfoModel,
    InvalidAuthentication,
    NoCameraFound,
    UnknownError,
)

from menuai import config_entries
from menuai.components.trafikverket_camera.const import DOMAIN
from menuai.const import CONF_API_KEY, CONF_ID, CONF_LOCATION
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(menuai: menuai, get_camera: CameraInfoModel) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.trafikverket_camera.config_flow.TrafikverketCamera.async_get_cameras",
            return_value=[get_camera],
        ),
        patch(
            "menuai.components.trafikverket_camera.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "1234567890",
                CONF_LOCATION: "Test loc",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Test Camera"
    assert result2["data"] == {
        "api_key": "1234567890",
        "id": "1234",
    }
    assert len(mock_setup_entry.mock_calls) == 1
    assert result2["result"].unique_id == "trafikverket_camera-1234"


async def test_form_multiple_cameras(
    menuai: menuai,
    get_cameras: list[CameraInfoModel],
    get_camera2: CameraInfoModel,
) -> None:
    """Test we get the form with multiple cameras."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.trafikverket_camera.config_flow.TrafikverketCamera.async_get_cameras",
        return_value=get_cameras,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "1234567890",
                CONF_LOCATION: "Test loc",
            },
        )
        await menuai.async_block_till_done()

    with (
        patch(
            "menuai.components.trafikverket_camera.config_flow.TrafikverketCamera.async_get_cameras",
            return_value=[get_camera2],
        ),
        patch(
            "menuai.components.trafikverket_camera.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ID: "5678",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Camera2"
    assert result["data"] == {
        "api_key": "1234567890",
        "id": "5678",
    }
    assert len(mock_setup_entry.mock_calls) == 1
    assert result["result"].unique_id == "trafikverket_camera-5678"


async def test_form_no_location_data(
    menuai: menuai, get_camera_no_location: CameraInfoModel
) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.trafikverket_camera.config_flow.TrafikverketCamera.async_get_cameras",
            return_value=[get_camera_no_location],
        ),
        patch(
            "menuai.components.trafikverket_camera.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "1234567890",
                CONF_LOCATION: "Test Cam",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Test Camera"
    assert result2["data"] == {
        "api_key": "1234567890",
        "id": "1234",
    }
    assert len(mock_setup_entry.mock_calls) == 1
    assert result2["result"].unique_id == "trafikverket_camera-1234"


@pytest.mark.parametrize(
    ("side_effect", "error_key", "base_error"),
    [
        (
            InvalidAuthentication,
            "base",
            "invalid_auth",
        ),
        (
            NoCameraFound,
            "location",
            "invalid_location",
        ),
        (
            UnknownError,
            "base",
            "cannot_connect",
        ),
    ],
)
async def test_flow_fails(
    menuai: menuai, side_effect: Exception, error_key: str, base_error: str
) -> None:
    """Test config flow errors."""
    result4 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result4["type"] is FlowResultType.FORM
    assert result4["step_id"] == config_entries.SOURCE_USER

    with patch(
        "menuai.components.trafikverket_camera.config_flow.TrafikverketCamera.async_get_cameras",
        side_effect=side_effect,
    ):
        result4 = await menuai.config_entries.flow.async_configure(
            result4["flow_id"],
            user_input={
                CONF_API_KEY: "1234567890",
                CONF_LOCATION: "incorrect",
            },
        )

    assert result4["errors"] == {error_key: base_error}


async def test_reauth_flow(menuai: menuai) -> None:
    """Test a reauthentication flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_KEY: "1234567890",
            CONF_ID: "1234",
        },
        unique_id="1234",
        version=3,
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.trafikverket_camera.config_flow.TrafikverketCamera.async_get_cameras",
        ),
        patch(
            "menuai.components.trafikverket_camera.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "1234567891"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert entry.data == {
        "api_key": "1234567891",
        "id": "1234",
    }


@pytest.mark.parametrize(
    ("side_effect", "error_key", "p_error"),
    [
        (
            InvalidAuthentication,
            "base",
            "invalid_auth",
        ),
        (
            NoCameraFound,
            "location",
            "invalid_location",
        ),
        (
            UnknownError,
            "base",
            "cannot_connect",
        ),
    ],
)
async def test_reauth_flow_error(
    menuai: menuai, side_effect: Exception, error_key: str, p_error: str
) -> None:
    """Test a reauthentication flow with error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_KEY: "1234567890",
            CONF_ID: "1234",
        },
        unique_id="1234",
        version=3,
    )
    entry.add_to_menuai(menuai)
    await menuai.async_block_till_done()

    result = await entry.start_reauth_flow(menuai)

    with patch(
        "menuai.components.trafikverket_camera.config_flow.TrafikverketCamera.async_get_cameras",
        side_effect=side_effect,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "1234567890"},
        )
        await menuai.async_block_till_done()

    assert result2["step_id"] == "reauth_confirm"
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {error_key: p_error}

    with (
        patch(
            "menuai.components.trafikverket_camera.config_flow.TrafikverketCamera.async_get_cameras",
        ),
        patch(
            "menuai.components.trafikverket_camera.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "1234567891"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert entry.data == {
        "api_key": "1234567891",
        "id": "1234",
    }


async def test_reconfigure_flow(
    menuai: menuai,
    get_cameras: list[CameraInfoModel],
    get_camera2: CameraInfoModel,
) -> None:
    """Test a reconfigure flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_KEY: "1234567890",
            CONF_ID: "1234",
        },
        unique_id="1234",
        version=3,
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)
    assert result["step_id"] == "reconfigure"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.trafikverket_camera.config_flow.TrafikverketCamera.async_get_cameras",
        return_value=get_cameras,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "1234567890",
                CONF_LOCATION: "Test loc",
            },
        )
        await menuai.async_block_till_done()

    with (
        patch(
            "menuai.components.trafikverket_camera.config_flow.TrafikverketCamera.async_get_cameras",
            return_value=[get_camera2],
        ),
        patch(
            "menuai.components.trafikverket_camera.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ID: "5678",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {
        "api_key": "1234567890",
        "id": "5678",
    }


@pytest.mark.parametrize(
    ("side_effect", "error_key", "p_error"),
    [
        (
            InvalidAuthentication,
            "base",
            "invalid_auth",
        ),
        (
            NoCameraFound,
            "location",
            "invalid_location",
        ),
        (
            UnknownError,
            "base",
            "cannot_connect",
        ),
    ],
)
async def test_reconfigure_flow_error(
    menuai: menuai,
    get_camera: CameraInfoModel,
    side_effect: Exception,
    error_key: str,
    p_error: str,
) -> None:
    """Test a reauthentication flow with error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_KEY: "1234567890",
            CONF_ID: "1234",
        },
        unique_id="1234",
        version=3,
    )
    entry.add_to_menuai(menuai)
    await menuai.async_block_till_done()

    result = await entry.start_reconfigure_flow(menuai)

    with patch(
        "menuai.components.trafikverket_camera.config_flow.TrafikverketCamera.async_get_cameras",
        side_effect=side_effect,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "1234567890",
                CONF_LOCATION: "Test loc",
            },
        )
        await menuai.async_block_till_done()

    assert result2["step_id"] == "reconfigure"
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {error_key: p_error}

    with (
        patch(
            "menuai.components.trafikverket_camera.config_flow.TrafikverketCamera.async_get_cameras",
            return_value=[get_camera],
        ),
        patch(
            "menuai.components.trafikverket_camera.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "1234567891",
                CONF_LOCATION: "Test loc",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reconfigure_successful"
    assert entry.data == {
        CONF_ID: "1234",
        CONF_API_KEY: "1234567891",
    }
