"""Test the Radio Thermostat config flow."""

from unittest.mock import MagicMock, patch

from radiotherm import CommonThermostat
from radiotherm.validate import RadiothermTstatError

from menuai import config_entries
from menuai.components.radiotherm.const import DOMAIN
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.dhcp import DhcpServiceInfo

from tests.common import MockConfigEntry


def _mock_radiotherm():
    tstat = MagicMock(autospec=CommonThermostat)
    tstat.name = {"raw": "My Name"}
    tstat.sys = {
        "raw": {"uuid": "aabbccddeeff", "fw_version": "1.2.3", "api_version": "4.5.6"}
    }
    tstat.model = {"raw": "Model"}
    return tstat


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.radiotherm.data.radiotherm.get_thermostat",
            return_value=_mock_radiotherm(),
        ),
        patch(
            "menuai.components.radiotherm.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.2.3.4",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "My Name"
    assert result2["data"] == {
        "host": "1.2.3.4",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_unknown_error(menuai: menuai) -> None:
    """Test we handle unknown error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.radiotherm.data.radiotherm.get_thermostat",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.2.3.4",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.radiotherm.data.radiotherm.get_thermostat",
        side_effect=RadiothermTstatError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.2.3.4",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {CONF_HOST: "cannot_connect"}


async def test_dhcp_can_confirm(menuai: menuai) -> None:
    """Test DHCP discovery flow can confirm right away."""

    with patch(
        "menuai.components.radiotherm.data.radiotherm.get_thermostat",
        return_value=_mock_radiotherm(),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(
                hostname="radiotherm",
                ip="1.2.3.4",
                macaddress="aabbccddeeff",
            ),
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert result["description_placeholders"] == {
        "host": "1.2.3.4",
        "name": "My Name",
        "model": "Model",
    }

    with patch(
        "menuai.components.radiotherm.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "My Name"
    assert result2["data"] == {
        "host": "1.2.3.4",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_dhcp_fails_to_connect(menuai: menuai) -> None:
    """Test DHCP discovery flow that fails to connect."""

    with patch(
        "menuai.components.radiotherm.data.radiotherm.get_thermostat",
        side_effect=RadiothermTstatError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(
                hostname="radiotherm",
                ip="1.2.3.4",
                macaddress="aabbccddeeff",
            ),
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_dhcp_already_exists(menuai: menuai) -> None:
    """Test DHCP discovery flow that fails to connect."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4"},
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.radiotherm.data.radiotherm.get_thermostat",
        return_value=_mock_radiotherm(),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(
                hostname="radiotherm",
                ip="1.2.3.4",
                macaddress="aabbccddeeff",
            ),
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_unique_id_already_exists(menuai: menuai) -> None:
    """Test creating an entry where the unique_id already exists."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4"},
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.radiotherm.data.radiotherm.get_thermostat",
            return_value=_mock_radiotherm(),
        ),
        patch(
            "menuai.components.radiotherm.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.2.3.4",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
