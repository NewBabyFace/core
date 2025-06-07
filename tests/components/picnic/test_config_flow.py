"""Test the Picnic config flow."""

from unittest.mock import patch

import pytest
from python_picnic_api2.session import PicnicAuthError
import requests

from menuai import config_entries
from menuai.components.picnic.const import DOMAIN
from menuai.const import CONF_ACCESS_TOKEN, CONF_COUNTRY_CODE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.fixture
def picnic_api():
    """Create PicnicAPI mock with set response data."""
    auth_token = "af3wh738j3fa28l9fa23lhiufahu7l"
    auth_data = {
        "user_id": "f29-2a6-o32n",
        "address": {
            "street": "Teststreet",
            "house_number": 123,
            "house_number_ext": "b",
        },
    }
    with patch(
        "menuai.components.picnic.config_flow.PicnicAPI",
    ) as picnic_mock:
        picnic_mock().session.auth_token = auth_token
        picnic_mock().get_user.return_value = auth_data

        yield picnic_mock


async def test_form(menuai: menuai, picnic_api) -> None:
    """Test we get the form and a config entry is created."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] is None

    with patch(
        "menuai.components.picnic.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country_code": "NL",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Picnic"
    assert result2["data"] == {
        CONF_ACCESS_TOKEN: picnic_api().session.auth_token,
        CONF_COUNTRY_CODE: "NL",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid authentication."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.picnic.config_flow.PicnicHub.authenticate",
        side_effect=PicnicAuthError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country_code": "NL",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle connection errors."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.picnic.config_flow.PicnicHub.authenticate",
        side_effect=requests.exceptions.ConnectionError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country_code": "NL",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_exception(menuai: menuai) -> None:
    """Test we handle random exceptions."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.picnic.config_flow.PicnicHub.authenticate",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country_code": "NL",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_form_already_configured(menuai: menuai, picnic_api) -> None:
    """Test that an entry with unique id can only be added once."""
    # Create a mocked config entry and make sure to use the same user_id as set for the picnic_api mock response.
    MockConfigEntry(
        domain=DOMAIN,
        unique_id=picnic_api().get_user()["user_id"],
        data={CONF_ACCESS_TOKEN: "a3p98fsen.a39p3fap", CONF_COUNTRY_CODE: "NL"},
    ).add_to_menuai(menuai)

    result_init = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result_configure = await menuai.config_entries.flow.async_configure(
        result_init["flow_id"],
        {
            "username": "test-username",
            "password": "test-password",
            "country_code": "NL",
        },
    )
    await menuai.async_block_till_done()

    assert result_configure["type"] is FlowResultType.ABORT
    assert result_configure["reason"] == "already_configured"


async def test_step_reauth(menuai: menuai, picnic_api) -> None:
    """Test the re-auth flow."""
    # Create a mocked config entry
    conf = {CONF_ACCESS_TOKEN: "a3p98fsen.a39p3fap", CONF_COUNTRY_CODE: "NL"}

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=picnic_api().get_user()["user_id"],
        data=conf,
    )
    entry.add_to_menuai(menuai)

    # Init a re-auth flow
    result_init = await entry.start_reauth_flow(menuai)
    assert result_init["type"] is FlowResultType.FORM
    assert result_init["step_id"] == "user"

    with patch(
        "menuai.components.picnic.async_setup_entry",
        return_value=True,
    ):
        result_configure = await menuai.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country_code": "NL",
            },
        )
        await menuai.async_block_till_done()

    # Check that the returned flow has type abort because of successful re-authentication
    assert result_configure["type"] is FlowResultType.ABORT
    assert result_configure["reason"] == "reauth_successful"

    assert len(menuai.config_entries.async_entries()) == 1


async def test_step_reauth_failed(menuai: menuai) -> None:
    """Test the re-auth flow when authentication fails."""
    # Create a mocked config entry
    user_id = "f29-2a6-o32n"
    conf = {CONF_ACCESS_TOKEN: "a3p98fsen.a39p3fap", CONF_COUNTRY_CODE: "NL"}

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=user_id,
        data=conf,
    )
    entry.add_to_menuai(menuai)

    # Init a re-auth flow
    result_init = await entry.start_reauth_flow(menuai)
    assert result_init["type"] is FlowResultType.FORM
    assert result_init["step_id"] == "user"

    with patch(
        "menuai.components.picnic.config_flow.PicnicHub.authenticate",
        side_effect=PicnicAuthError,
    ):
        result_configure = await menuai.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country_code": "NL",
            },
        )
        await menuai.async_block_till_done()

    # Check that the returned flow has type form with error set
    assert result_configure["type"] is FlowResultType.FORM
    assert result_configure["errors"] == {"base": "invalid_auth"}

    assert len(menuai.config_entries.async_entries()) == 1


async def test_step_reauth_different_account(menuai: menuai, picnic_api) -> None:
    """Test the re-auth flow when authentication is done with a different account."""
    # Create a mocked config entry, unique_id should be different that the user id in the api response
    conf = {CONF_ACCESS_TOKEN: "a3p98fsen.a39p3fap", CONF_COUNTRY_CODE: "NL"}

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="3fpawh-ues-af3ho",
        data=conf,
    )
    entry.add_to_menuai(menuai)

    # Init a re-auth flow
    result_init = await entry.start_reauth_flow(menuai)
    assert result_init["type"] is FlowResultType.FORM
    assert result_init["step_id"] == "user"

    with patch(
        "menuai.components.picnic.async_setup_entry",
        return_value=True,
    ):
        result_configure = await menuai.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country_code": "NL",
            },
        )
        await menuai.async_block_till_done()

    # Check that the returned flow has type form with error set
    assert result_configure["type"] is FlowResultType.FORM
    assert result_configure["errors"] == {"base": "different_account"}

    assert len(menuai.config_entries.async_entries()) == 1
