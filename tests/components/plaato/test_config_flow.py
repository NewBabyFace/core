"""Test the Plaato config flow."""

from unittest.mock import patch

from pyplaato.models.device import PlaatoDeviceType
import pytest

from menuai import config_entries
from menuai.components.plaato.const import (
    CONF_DEVICE_NAME,
    CONF_DEVICE_TYPE,
    CONF_USE_WEBHOOK,
    DOMAIN,
)
from menuai.const import CONF_SCAN_INTERVAL, CONF_TOKEN, CONF_WEBHOOK_ID
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry

BASE_URL = "http://example.com"
WEBHOOK_ID = "webhook_id"
UNIQUE_ID = "plaato_unique_id"


@pytest.fixture(name="webhook_id")
def mock_webhook_id():
    """Mock webhook_id."""
    with (
        patch(
            "menuai.components.webhook.async_generate_id",
            return_value=WEBHOOK_ID,
        ),
        patch(
            "menuai.components.webhook.async_generate_url",
            return_value="hook_id",
        ),
    ):
        yield


async def test_show_config_form(menuai: menuai) -> None:
    """Test show configuration form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_show_config_form_device_type_airlock(menuai: menuai) -> None:
    """Test show configuration form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_DEVICE_TYPE: PlaatoDeviceType.Airlock,
            CONF_DEVICE_NAME: "device_name",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "api_method"
    assert result["data_schema"].schema.get(CONF_TOKEN) is str
    assert result["data_schema"].schema.get(CONF_USE_WEBHOOK) is bool


async def test_show_config_form_device_type_keg(menuai: menuai) -> None:
    """Test show configuration form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_DEVICE_TYPE: PlaatoDeviceType.Keg, CONF_DEVICE_NAME: "device_name"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "api_method"
    assert result["data_schema"].schema.get(CONF_TOKEN) is str
    assert result["data_schema"].schema.get(CONF_USE_WEBHOOK) is None


async def test_show_config_form_validate_webhook(
    menuai: menuai, webhook_id
) -> None:
    """Test show configuration form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE_TYPE: PlaatoDeviceType.Airlock,
            CONF_DEVICE_NAME: "device_name",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "api_method"

    assert await async_setup_component(menuai, "cloud", {})
    with (
        patch(
            "menuai.components.cloud.async_active_subscription",
            return_value=True,
        ),
        patch("menuai.components.cloud.async_is_logged_in", return_value=True),
        patch("menuai.components.cloud.async_is_connected", return_value=True),
        patch(
            "menuai_nabucasa.cloudhooks.Cloudhooks.async_create",
            return_value={"cloudhook_url": "https://hooks.nabu.casa/ABCD"},
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_TOKEN: "",
                CONF_USE_WEBHOOK: True,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "webhook"


async def test_show_config_form_validate_webhook_not_connected(
    menuai: menuai, webhook_id
) -> None:
    """Test validating webhook when not connected aborts."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE_TYPE: PlaatoDeviceType.Airlock,
            CONF_DEVICE_NAME: "device_name",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "api_method"

    assert await async_setup_component(menuai, "cloud", {})
    with (
        patch(
            "menuai.components.cloud.async_active_subscription",
            return_value=True,
        ),
        patch("menuai.components.cloud.async_is_logged_in", return_value=True),
        patch("menuai.components.cloud.async_is_connected", return_value=False),
        patch(
            "menuai_nabucasa.cloudhooks.Cloudhooks.async_create",
            return_value={"cloudhook_url": "https://hooks.nabu.casa/ABCD"},
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_TOKEN: "",
                CONF_USE_WEBHOOK: True,
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cloud_not_connected"


async def test_show_config_form_validate_token(menuai: menuai) -> None:
    """Test show configuration form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE_TYPE: PlaatoDeviceType.Keg,
            CONF_DEVICE_NAME: "device_name",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "api_method"

    with patch("menuai.components.plaato.async_setup_entry", return_value=True):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_TOKEN: "valid_token"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == PlaatoDeviceType.Keg.name
    assert result["data"] == {
        CONF_USE_WEBHOOK: False,
        CONF_TOKEN: "valid_token",
        CONF_DEVICE_TYPE: PlaatoDeviceType.Keg,
        CONF_DEVICE_NAME: "device_name",
    }


async def test_show_config_form_no_cloud_webhook(
    menuai: menuai, webhook_id
) -> None:
    """Test show configuration form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE_TYPE: PlaatoDeviceType.Airlock,
            CONF_DEVICE_NAME: "device_name",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "api_method"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_USE_WEBHOOK: True,
            CONF_TOKEN: "",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "webhook"
    assert result["errors"] is None


async def test_show_config_form_api_method_no_auth_token(
    menuai: menuai, webhook_id
) -> None:
    """Test show configuration form."""

    # Using Keg
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE_TYPE: PlaatoDeviceType.Keg,
            CONF_DEVICE_NAME: "device_name",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "api_method"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_TOKEN: ""}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "api_method"
    assert len(result["errors"]) == 1
    assert result["errors"]["base"] == "no_auth_token"

    # Using Airlock
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_DEVICE_TYPE: PlaatoDeviceType.Airlock,
            CONF_DEVICE_NAME: "device_name",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "api_method"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_TOKEN: ""}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "api_method"
    assert len(result["errors"]) == 1
    assert result["errors"]["base"] == "no_api_method"


async def test_options(menuai: menuai) -> None:
    """Test updating options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="NAME",
        data={},
        options={CONF_SCAN_INTERVAL: 5},
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.plaato.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        result = await menuai.config_entries.options.async_init(config_entry.entry_id)

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_SCAN_INTERVAL: 10},
        )

        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_SCAN_INTERVAL] == 10

        assert len(mock_setup_entry.mock_calls) == 1


async def test_options_webhook(menuai: menuai, webhook_id) -> None:
    """Test updating options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="NAME",
        data={CONF_USE_WEBHOOK: True, CONF_WEBHOOK_ID: None},
        options={CONF_SCAN_INTERVAL: 5},
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.plaato.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        result = await menuai.config_entries.options.async_init(config_entry.entry_id)

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "webhook"
        assert result["description_placeholders"] == {"webhook_url": ""}

        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_WEBHOOK_ID: WEBHOOK_ID},
        )

        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_WEBHOOK_ID] == CONF_WEBHOOK_ID

        assert len(mock_setup_entry.mock_calls) == 1
