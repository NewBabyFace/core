"""Test the Tesla Wall Connector config flow."""

from unittest.mock import patch

from tesla_wall_connector.exceptions import WallConnectorConnectionError

from menuai import config_entries
from menuai.components.tesla_wall_connector.const import DOMAIN
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.dhcp import DhcpServiceInfo

from tests.common import MockConfigEntry


async def test_form(mock_wall_connector_version, menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "menuai.components.tesla_wall_connector.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Tesla Wall Connector"
    assert result2["data"] == {CONF_HOST: "1.1.1.1"}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "tesla_wall_connector.WallConnector.async_get_version",
        side_effect=WallConnectorConnectionError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_other_error(
    mock_wall_connector_version, menuai: menuai
) -> None:
    """Test we handle any other error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "tesla_wall_connector.WallConnector.async_get_version",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_form_already_configured(
    mock_wall_connector_setup, mock_wall_connector_version, menuai: menuai
) -> None:
    """Test we get already configured."""

    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="abc123", data={CONF_HOST: "0.0.0.0"}
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "1.1.1.1"},
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"

    # Test config entry got updated with latest IP
    assert entry.data[CONF_HOST] == "1.1.1.1"


async def test_dhcp_can_finish(
    mock_wall_connector_setup, mock_wall_connector_version, menuai: menuai
) -> None:
    """Test DHCP discovery flow can finish right away."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data=DhcpServiceInfo(
            hostname="teslawallconnector_abc",
            ip="1.2.3.4",
            macaddress="aadc44271212",
        ),
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: "1.2.3.4"}


async def test_dhcp_already_exists(
    mock_wall_connector_version, menuai: menuai
) -> None:
    """Test DHCP discovery flow when device already exists."""

    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="abc123", data={CONF_HOST: "1.2.3.4"}
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_DHCP},
        data=DhcpServiceInfo(
            hostname="teslawallconnector_aabbcc",
            ip="1.2.3.4",
            macaddress="aabbccddeeff",
        ),
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_dhcp_error_from_wall_connector(
    mock_wall_connector_version, menuai: menuai
) -> None:
    """Test DHCP discovery flow when we cannot communicate with the device."""

    with patch(
        "tesla_wall_connector.WallConnector.async_get_version",
        side_effect=WallConnectorConnectionError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(
                hostname="teslawallconnector_aabbcc",
                ip="1.2.3.4",
                macaddress="aabbccddeeff",
            ),
        )
        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "cannot_connect"
