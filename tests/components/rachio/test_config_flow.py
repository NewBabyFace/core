"""Test the Rachio config flow."""

from ipaddress import ip_address
from unittest.mock import MagicMock, patch

from menuai import config_entries
from menuai.components.rachio.const import (
    CONF_CUSTOM_URL,
    CONF_MANUAL_RUN_MINS,
    DOMAIN,
)
from menuai.const import CONF_API_KEY
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.zeroconf import (
    ATTR_PROPERTIES_ID,
    ZeroconfServiceInfo,
)

from tests.common import MockConfigEntry


def _mock_rachio_return_value(get=None, info=None):
    rachio_mock = MagicMock()
    person_mock = MagicMock()
    type(person_mock).get = MagicMock(return_value=get)
    type(person_mock).info = MagicMock(return_value=info)
    type(rachio_mock).person = person_mock
    return rachio_mock


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    rachio_mock = _mock_rachio_return_value(
        get=({"status": 200}, {"username": "myusername"}),
        info=({"status": 200}, {"id": "myid"}),
    )

    with (
        patch(
            "menuai.components.rachio.config_flow.Rachio",
            return_value=rachio_mock,
        ),
        patch(
            "menuai.components.rachio.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "api_key",
                CONF_CUSTOM_URL: "http://custom.url",
                CONF_MANUAL_RUN_MINS: 5,
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "myusername"
    assert result2["data"] == {
        CONF_API_KEY: "api_key",
        CONF_CUSTOM_URL: "http://custom.url",
        CONF_MANUAL_RUN_MINS: 5,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    rachio_mock = _mock_rachio_return_value(
        get=({"status": 200}, {"username": "myusername"}),
        info=({"status": 412}, {"error": "auth fail"}),
    )
    with patch(
        "menuai.components.rachio.config_flow.Rachio", return_value=rachio_mock
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "api_key"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    rachio_mock = _mock_rachio_return_value(
        get=({"status": 599}, {"username": "myusername"}),
        info=({"status": 200}, {"id": "myid"}),
    )
    with patch(
        "menuai.components.rachio.config_flow.Rachio", return_value=rachio_mock
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "api_key"},
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_homekit(menuai: menuai) -> None:
    """Test that we abort from homekit if rachio is already setup."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_HOMEKIT},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("127.0.0.1"),
            ip_addresses=[ip_address("127.0.0.1")],
            hostname="mock_hostname",
            name="mock_name",
            port=None,
            properties={ATTR_PROPERTIES_ID: "AA:BB:CC:DD:EE:FF"},
            type="mock_type",
        ),
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    flow = next(
        flow
        for flow in menuai.config_entries.flow.async_progress()
        if flow["flow_id"] == result["flow_id"]
    )
    assert flow["context"]["unique_id"] == "AA:BB:CC:DD:EE:FF"

    entry = MockConfigEntry(domain=DOMAIN, data={CONF_API_KEY: "api_key"})
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_HOMEKIT},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("127.0.0.1"),
            ip_addresses=[ip_address("127.0.0.1")],
            hostname="mock_hostname",
            name="mock_name",
            port=None,
            properties={ATTR_PROPERTIES_ID: "AA:BB:CC:DD:EE:FF"},
            type="mock_type",
        ),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_form_homekit_ignored(menuai: menuai) -> None:
    """Test that we abort from homekit if rachio is ignored."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AA:BB:CC:DD:EE:FF",
        source=config_entries.SOURCE_IGNORE,
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_HOMEKIT},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("127.0.0.1"),
            ip_addresses=[ip_address("127.0.0.1")],
            hostname="mock_hostname",
            name="mock_name",
            port=None,
            properties={ATTR_PROPERTIES_ID: "AA:BB:CC:DD:EE:FF"},
            type="mock_type",
        ),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(menuai: menuai) -> None:
    """Test option flow."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_API_KEY: "api_key"})
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    # This should be improved at a later stage to increase test coverage
    menuai.config_entries.options.async_abort(result["flow_id"])
