"""Test the AirTouch 4 config flow."""

from unittest.mock import AsyncMock, Mock, patch

from airtouch4pyapi.airtouch import AirTouch, AirTouchAc, AirTouchGroup, AirTouchStatus

from menuai import config_entries
from menuai.components.airtouch4.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None
    mock_ac = AirTouchAc()
    mock_groups = AirTouchGroup()
    mock_airtouch = AirTouch("")
    mock_airtouch.UpdateInfo = AsyncMock()
    mock_airtouch.Status = AirTouchStatus.OK
    mock_airtouch.GetAcs = Mock(return_value=[mock_ac])
    mock_airtouch.GetGroups = Mock(return_value=[mock_groups])

    with (
        patch(
            "menuai.components.airtouch4.config_flow.AirTouch",
            return_value=mock_airtouch,
        ),
        patch(
            "menuai.components.airtouch4.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {"host": "0.0.0.1"}
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "0.0.0.1"
    assert result2["data"] == {
        "host": "0.0.0.1",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_timeout(menuai: menuai) -> None:
    """Test we handle a connection timeout."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    mock_airtouch = AirTouch("")
    mock_airtouch.UpdateInfo = AsyncMock()
    mock_airtouch.status = AirTouchStatus.CONNECTION_INTERRUPTED
    with patch(
        "menuai.components.airtouch4.config_flow.AirTouch",
        return_value=mock_airtouch,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {"host": "0.0.0.1"}
        )
        assert result2["type"] is FlowResultType.FORM
        assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_library_error_message(menuai: menuai) -> None:
    """Test we handle an unknown error message from the library."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    mock_airtouch = AirTouch("")
    mock_airtouch.UpdateInfo = AsyncMock()
    mock_airtouch.status = AirTouchStatus.ERROR
    with patch(
        "menuai.components.airtouch4.config_flow.AirTouch",
        return_value=mock_airtouch,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {"host": "0.0.0.1"}
        )
        assert result2["type"] is FlowResultType.FORM
        assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_connection_refused(menuai: menuai) -> None:
    """Test we handle a connection error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    mock_airtouch = AirTouch("")
    mock_airtouch.UpdateInfo = AsyncMock()
    mock_airtouch.status = AirTouchStatus.NOT_CONNECTED
    with patch(
        "menuai.components.airtouch4.config_flow.AirTouch",
        return_value=mock_airtouch,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {"host": "0.0.0.1"}
        )
        assert result2["type"] is FlowResultType.FORM
        assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_no_units(menuai: menuai) -> None:
    """Test we handle no units found."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    mock_ac = AirTouchAc()
    mock_airtouch = AirTouch("")
    mock_airtouch.UpdateInfo = AsyncMock()
    mock_airtouch.Status = AirTouchStatus.OK
    mock_airtouch.GetAcs = Mock(return_value=[mock_ac])
    mock_airtouch.GetGroups = Mock(return_value=[])

    with patch(
        "menuai.components.airtouch4.config_flow.AirTouch",
        return_value=mock_airtouch,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {"host": "0.0.0.1"}
        )

        assert result2["type"] is FlowResultType.FORM
        assert result2["errors"] == {"base": "no_units"}
