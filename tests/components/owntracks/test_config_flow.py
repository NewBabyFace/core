"""Tests for OwnTracks config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.owntracks import config_flow
from menuai.components.owntracks.config_flow import CONF_CLOUDHOOK, CONF_SECRET
from menuai.components.owntracks.const import DOMAIN
from menuai.const import CONF_WEBHOOK_ID
from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config
from menuai.data_entry_flow import FlowResultType
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry

CONF_WEBHOOK_URL = "webhook_url"

BASE_URL = "http://example.com"
CLOUDHOOK = False
SECRET = "test-secret"
WEBHOOK_ID = "webhook_id"
WEBHOOK_URL = f"{BASE_URL}/api/webhook/webhook_id"


@pytest.fixture(name="webhook_id")
def mock_webhook_id():
    """Mock webhook_id."""
    with patch(
        "menuai.components.webhook.async_generate_id", return_value=WEBHOOK_ID
    ):
        yield


@pytest.fixture(name="secret")
def mock_secret():
    """Mock secret."""
    with patch("secrets.token_hex", return_value=SECRET):
        yield


@pytest.fixture(name="not_supports_encryption")
def mock_not_supports_encryption():
    """Mock non successful nacl import."""
    with patch(
        "menuai.components.owntracks.config_flow.supports_encryption",
        return_value=False,
    ):
        yield


async def init_config_flow(menuai: menuai) -> config_flow.OwnTracksFlow:
    """Init a configuration flow."""
    await async_process_ha_core_config(
        menuai,
        {"external_url": BASE_URL},
    )
    flow = config_flow.OwnTracksFlow()
    flow.menuai = menuai
    return flow


async def test_user(menuai: menuai, webhook_id, secret) -> None:
    """Test user step."""
    flow = await init_config_flow(menuai)

    result = await flow.async_step_user()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await flow.async_step_user({})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "OwnTracks"
    assert result["data"][CONF_WEBHOOK_ID] == WEBHOOK_ID
    assert result["data"][CONF_SECRET] == SECRET
    assert result["data"][CONF_CLOUDHOOK] == CLOUDHOOK
    assert result["description_placeholders"][CONF_WEBHOOK_URL] == WEBHOOK_URL


async def test_import_setup(menuai: menuai) -> None:
    """Test that we don't automatically create a config entry."""
    await async_process_ha_core_config(
        menuai,
        {"external_url": "http://example.com"},
    )

    assert not menuai.config_entries.async_entries(DOMAIN)
    assert await async_setup_component(menuai, DOMAIN, {"owntracks": {}})
    await menuai.async_block_till_done()
    assert not menuai.config_entries.async_entries(DOMAIN)


async def test_abort_if_already_setup(menuai: menuai) -> None:
    """Test that we can't add more than one instance."""
    MockConfigEntry(domain=DOMAIN, data={}).add_to_menuai(menuai)
    assert menuai.config_entries.async_entries(DOMAIN)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Should fail, already setup (flow)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_user_not_supports_encryption(
    menuai: menuai, not_supports_encryption
) -> None:
    """Test user step."""
    flow = await init_config_flow(menuai)

    result = await flow.async_step_user({})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert (
        result["description_placeholders"]["secret"]
        == "Encryption is not supported because nacl is not installed."
    )


async def test_unload(menuai: menuai) -> None:
    """Test unloading a config flow."""
    await async_process_ha_core_config(
        menuai,
        {"external_url": "http://example.com"},
    )

    with patch(
        "menuai.config_entries.ConfigEntries.async_forward_entry_setups"
    ) as mock_forward:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data={}
        )

    assert len(mock_forward.mock_calls) == 1
    entry = result["result"]

    mock_forward.assert_called_once_with(entry, ["device_tracker"])
    assert entry.data["webhook_id"] in menuai.data["webhook"]

    with patch(
        "menuai.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ) as mock_unload:
        assert await menuai.config_entries.async_unload(entry.entry_id)

    assert len(mock_unload.mock_calls) == 1
    mock_forward.assert_called_once_with(entry, ["device_tracker"])
    assert entry.data["webhook_id"] not in menuai.data["webhook"]


async def test_with_cloud_sub(menuai: menuai) -> None:
    """Test creating a config flow while subscribed."""
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
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data={}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert entry.data["cloudhook"]
    assert (
        result["description_placeholders"]["webhook_url"]
        == "https://hooks.nabu.casa/ABCD"
    )


async def test_with_cloud_sub_not_connected(menuai: menuai) -> None:
    """Test creating a config flow while subscribed."""
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
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data={}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cloud_not_connected"
