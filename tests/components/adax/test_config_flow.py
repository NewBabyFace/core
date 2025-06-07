"""Test the Adax config flow."""

from unittest.mock import patch

import adax_local

from menuai import config_entries
from menuai.components.adax.const import (
    ACCOUNT_ID,
    CLOUD,
    CONNECTION_TYPE,
    DOMAIN,
    LOCAL,
    WIFI_PSWD,
    WIFI_SSID,
)
from menuai.const import CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

TEST_DATA = {
    ACCOUNT_ID: 12345,
    CONF_PASSWORD: "pswd",
}


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONNECTION_TYPE: CLOUD,
        },
    )
    assert result2["type"] is FlowResultType.FORM

    with (
        patch(
            "adax.get_adax_token",
            return_value="test_token",
        ),
        patch(
            "menuai.components.adax.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            TEST_DATA,
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == str(TEST_DATA["account_id"])
    assert result3["data"] == {
        ACCOUNT_ID: TEST_DATA["account_id"],
        CONF_PASSWORD: TEST_DATA["password"],
        CONNECTION_TYPE: CLOUD,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONNECTION_TYPE: CLOUD,
        },
    )
    assert result2["type"] is FlowResultType.FORM

    with patch(
        "adax.get_adax_token",
        return_value=None,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            TEST_DATA,
        )
    assert result3["type"] is FlowResultType.FORM
    assert result3["errors"] == {"base": "cannot_connect"}


async def test_flow_entry_already_exists(menuai: menuai) -> None:
    """Test user input for config_entry that already exists."""

    first_entry = MockConfigEntry(
        domain="adax",
        data=TEST_DATA,
        unique_id=str(TEST_DATA[ACCOUNT_ID]),
    )
    first_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONNECTION_TYPE: CLOUD,
        },
    )
    assert result2["type"] is FlowResultType.FORM

    with patch("adax.get_adax_token", return_value="token"):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            TEST_DATA,
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "already_configured"


# local API:


async def test_local_create_entry(menuai: menuai) -> None:
    """Test create entry from user input."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONNECTION_TYPE: LOCAL,
        },
    )
    assert result2["type"] is FlowResultType.FORM

    test_data = {
        WIFI_SSID: "ssid",
        WIFI_PSWD: "pswd",
    }

    with (
        patch(
            "menuai.components.adax.async_setup_entry",
            return_value=True,
        ),
        patch(
            "menuai.components.adax.config_flow.adax_local.AdaxConfig",
            autospec=True,
        ) as mock_client_class,
    ):
        client = mock_client_class.return_value
        client.configure_device.return_value = True
        client.device_ip = "192.168.1.4"
        client.access_token = "token"
        client.mac_id = "8383838"
        result = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            test_data,
        )

    test_data[CONNECTION_TYPE] = LOCAL
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "8383838"
    assert result["data"] == {
        "connection_type": "Local",
        "ip_address": "192.168.1.4",
        "token": "token",
        "unique_id": "8383838",
    }


async def test_local_flow_entry_already_exists(menuai: menuai) -> None:
    """Test user input for config_entry that already exists."""

    test_data = {
        WIFI_SSID: "ssid",
        WIFI_PSWD: "pswd",
    }

    first_entry = MockConfigEntry(
        domain="adax",
        data=test_data,
        unique_id="8383838",
    )
    first_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONNECTION_TYPE: LOCAL,
        },
    )
    assert result2["type"] is FlowResultType.FORM

    test_data = {
        WIFI_SSID: "ssid",
        WIFI_PSWD: "pswd",
    }

    with patch("adax_local.AdaxConfig", autospec=True) as mock_client_class:
        client = mock_client_class.return_value
        client.configure_device.return_value = True
        client.device_ip = "192.168.1.4"
        client.access_token = "token"
        client.mac_id = "8383838"

        result = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            test_data,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_local_connection_error(menuai: menuai) -> None:
    """Test connection error."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONNECTION_TYPE: LOCAL,
        },
    )
    assert result2["type"] is FlowResultType.FORM

    test_data = {
        WIFI_SSID: "ssid",
        WIFI_PSWD: "pswd",
    }

    with patch(
        "menuai.components.adax.config_flow.adax_local.AdaxConfig.configure_device",
        return_value=False,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            test_data,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_local_heater_not_available(menuai: menuai) -> None:
    """Test connection error."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONNECTION_TYPE: LOCAL,
        },
    )
    assert result2["type"] is FlowResultType.FORM

    test_data = {
        WIFI_SSID: "ssid",
        WIFI_PSWD: "pswd",
    }

    with patch(
        "menuai.components.adax.config_flow.adax_local.AdaxConfig.configure_device",
        side_effect=adax_local.HeaterNotAvailable,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            test_data,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "heater_not_available"


async def test_local_heater_not_found(menuai: menuai) -> None:
    """Test connection error."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONNECTION_TYPE: LOCAL,
        },
    )
    assert result2["type"] is FlowResultType.FORM

    test_data = {
        WIFI_SSID: "ssid",
        WIFI_PSWD: "pswd",
    }

    with patch(
        "menuai.components.adax.config_flow.adax_local.AdaxConfig.configure_device",
        side_effect=adax_local.HeaterNotFound,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            test_data,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "heater_not_found"


async def test_local_invalid_wifi_cred(menuai: menuai) -> None:
    """Test connection error."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONNECTION_TYPE: LOCAL,
        },
    )
    assert result2["type"] is FlowResultType.FORM

    test_data = {
        WIFI_SSID: "ssid",
        WIFI_PSWD: "pswd",
    }

    with patch(
        "menuai.components.adax.config_flow.adax_local.AdaxConfig.configure_device",
        side_effect=adax_local.InvalidWifiCred,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            test_data,
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_auth"
