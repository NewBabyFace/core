"""Tests for the Config Entry Flow helper."""

import asyncio
from collections.abc import Callable, Generator
from contextlib import contextmanager
from unittest.mock import Mock, PropertyMock, patch

import pytest

from menuai import config_entries, data_entry_flow, setup
from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config
from menuai.helpers import config_entry_flow

from tests.common import MockConfigEntry, MockModule, mock_integration, mock_platform


@contextmanager
def _make_discovery_flow_conf(
    has_discovered_devices: Callable[[], asyncio.Future[bool] | bool],
) -> Generator[None]:
    with patch.dict(config_entries.HANDLERS):
        config_entry_flow.register_discovery_flow(
            "test", "Test", has_discovered_devices
        )
        yield


@pytest.fixture
def async_discovery_flow_conf(menuai: menuai) -> Generator[dict[str, bool]]:
    """Register a handler with an async discovery function."""
    handler_conf = {"discovered": False}

    async def has_discovered_devices(menuai: menuai) -> bool:
        """Mock if we have discovered devices."""
        return handler_conf["discovered"]

    with _make_discovery_flow_conf(has_discovered_devices):
        yield handler_conf


@pytest.fixture
def discovery_flow_conf(menuai: menuai) -> Generator[dict[str, bool]]:
    """Register a handler with a async friendly callback function."""
    handler_conf = {"discovered": False}

    def has_discovered_devices(menuai: menuai) -> bool:
        """Mock if we have discovered devices."""
        return handler_conf["discovered"]

    with _make_discovery_flow_conf(has_discovered_devices):
        yield handler_conf
    handler_conf = {"discovered": False}


@pytest.fixture
def webhook_flow_conf(menuai: menuai) -> Generator[None]:
    """Register a handler."""
    with patch.dict(config_entries.HANDLERS):
        config_entry_flow.register_webhook_flow("test_single", "Test Single", {}, False)
        config_entry_flow.register_webhook_flow(
            "test_multiple", "Test Multiple", {}, True
        )
        yield


async def test_single_entry_allowed(
    menuai: menuai, discovery_flow_conf: dict[str, bool]
) -> None:
    """Test only a single entry is allowed."""
    flow = config_entries.HANDLERS["test"]()
    flow.menuai = menuai
    flow.context = {}

    MockConfigEntry(domain="test").add_to_menuai(menuai)
    result = await flow.async_step_user()

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_user_no_devices_found(
    menuai: menuai, discovery_flow_conf: dict[str, bool]
) -> None:
    """Test if no devices found."""
    flow = config_entries.HANDLERS["test"]()
    flow.menuai = menuai
    flow.context = {"source": config_entries.SOURCE_USER}
    result = await flow.async_step_confirm(user_input={})

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_user_has_confirmation(
    menuai: menuai, discovery_flow_conf: dict[str, bool]
) -> None:
    """Test user requires confirmation to setup."""
    discovery_flow_conf["discovered"] = True
    mock_platform(menuai, "test.config_flow", None)

    result = await menuai.config_entries.flow.async_init(
        "test", context={"source": config_entries.SOURCE_USER}, data={}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "confirm"

    progress = menuai.config_entries.flow.async_progress()
    assert len(progress) == 1
    assert progress[0]["flow_id"] == result["flow_id"]
    assert progress[0]["context"] == {
        "confirm_only": True,
        "source": config_entries.SOURCE_USER,
        "unique_id": "test",
    }

    result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY


async def test_user_has_confirmation_async_discovery_flow(
    menuai: menuai, async_discovery_flow_conf: dict[str, bool]
) -> None:
    """Test user requires confirmation to setup with an async has_discovered_devices."""
    async_discovery_flow_conf["discovered"] = True
    mock_platform(menuai, "test.config_flow", None)

    result = await menuai.config_entries.flow.async_init(
        "test", context={"source": config_entries.SOURCE_USER}, data={}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "confirm"

    progress = menuai.config_entries.flow.async_progress()
    assert len(progress) == 1
    assert progress[0]["flow_id"] == result["flow_id"]
    assert progress[0]["context"] == {
        "confirm_only": True,
        "source": config_entries.SOURCE_USER,
        "unique_id": "test",
    }

    result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    "source",
    [
        config_entries.SOURCE_BLUETOOTH,
        config_entries.SOURCE_DISCOVERY,
        config_entries.SOURCE_MQTT,
        config_entries.SOURCE_SSDP,
        config_entries.SOURCE_ZEROCONF,
        config_entries.SOURCE_DHCP,
    ],
)
async def test_discovery_single_instance(
    menuai: menuai, discovery_flow_conf: dict[str, bool], source: str
) -> None:
    """Test we not allow duplicates."""
    flow = config_entries.HANDLERS["test"]()
    flow.menuai = menuai
    flow.context = {}

    MockConfigEntry(domain="test").add_to_menuai(menuai)
    result = await getattr(flow, f"async_step_{source}")({})

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


@pytest.mark.parametrize(
    "source",
    [
        config_entries.SOURCE_BLUETOOTH,
        config_entries.SOURCE_DISCOVERY,
        config_entries.SOURCE_MQTT,
        config_entries.SOURCE_SSDP,
        config_entries.SOURCE_ZEROCONF,
        config_entries.SOURCE_DHCP,
    ],
)
async def test_discovery_confirmation(
    menuai: menuai, discovery_flow_conf: dict[str, bool], source: str
) -> None:
    """Test we ask for confirmation via discovery."""
    flow = config_entries.HANDLERS["test"]()
    flow.menuai = menuai
    flow.context = {"source": source}

    result = await getattr(flow, f"async_step_{source}")({})

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "confirm"

    result = await flow.async_step_confirm({})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    "source",
    [
        config_entries.SOURCE_BLUETOOTH,
        config_entries.SOURCE_DISCOVERY,
        config_entries.SOURCE_MQTT,
        config_entries.SOURCE_SSDP,
        config_entries.SOURCE_ZEROCONF,
        config_entries.SOURCE_DHCP,
    ],
)
async def test_discovery_during_onboarding(
    menuai: menuai, discovery_flow_conf: dict[str, bool], source: str
) -> None:
    """Test we create config entry via discovery during onboarding."""
    flow = config_entries.HANDLERS["test"]()
    flow.menuai = menuai
    flow.context = {"source": source}

    with patch(
        "menuai.components.onboarding.async_is_onboarded", return_value=False
    ):
        result = await getattr(flow, f"async_step_{source}")({})

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY


async def test_multiple_discoveries(
    menuai: menuai, discovery_flow_conf: dict[str, bool]
) -> None:
    """Test we only create one instance for multiple discoveries."""
    mock_platform(menuai, "test.config_flow", None)

    result = await menuai.config_entries.flow.async_init(
        "test", context={"source": config_entries.SOURCE_DISCOVERY}, data={}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    # Second discovery
    result = await menuai.config_entries.flow.async_init(
        "test", context={"source": config_entries.SOURCE_DISCOVERY}, data={}
    )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT


async def test_only_one_in_progress(
    menuai: menuai, discovery_flow_conf: dict[str, bool]
) -> None:
    """Test a user initialized one will finish and cancel discovered one."""
    mock_platform(menuai, "test.config_flow", None)

    # Discovery starts flow
    result = await menuai.config_entries.flow.async_init(
        "test", context={"source": config_entries.SOURCE_DISCOVERY}, data={}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    # User starts flow
    result = await menuai.config_entries.flow.async_init(
        "test", context={"source": config_entries.SOURCE_USER}, data={}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM

    # Discovery flow has not been aborted
    assert len(menuai.config_entries.flow.async_progress()) == 2

    # Discovery should be aborted once user confirms
    result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert len(menuai.config_entries.flow.async_progress()) == 0


async def test_import_abort_discovery(
    menuai: menuai, discovery_flow_conf: dict[str, bool]
) -> None:
    """Test import will finish and cancel discovered one."""
    mock_platform(menuai, "test.config_flow", None)

    # Discovery starts flow
    result = await menuai.config_entries.flow.async_init(
        "test", context={"source": config_entries.SOURCE_DISCOVERY}, data={}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    # Start import flow
    result = await menuai.config_entries.flow.async_init(
        "test", context={"source": config_entries.SOURCE_IMPORT}, data={}
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY

    # Discovery flow has been aborted
    assert len(menuai.config_entries.flow.async_progress()) == 0


async def test_import_no_confirmation(
    menuai: menuai, discovery_flow_conf: dict[str, bool]
) -> None:
    """Test import requires no confirmation to set up."""
    flow = config_entries.HANDLERS["test"]()
    flow.menuai = menuai
    flow.context = {}
    discovery_flow_conf["discovered"] = True

    result = await flow.async_step_import(None)
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY


async def test_import_single_instance(
    menuai: menuai, discovery_flow_conf: dict[str, bool]
) -> None:
    """Test import doesn't create second instance."""
    flow = config_entries.HANDLERS["test"]()
    flow.menuai = menuai
    flow.context = {}
    discovery_flow_conf["discovered"] = True
    MockConfigEntry(domain="test").add_to_menuai(menuai)

    result = await flow.async_step_import(None)
    assert result["type"] == data_entry_flow.FlowResultType.ABORT


async def test_ignored_discoveries(
    menuai: menuai, discovery_flow_conf: dict[str, bool]
) -> None:
    """Test we can ignore discovered entries."""
    mock_platform(menuai, "test.config_flow", None)

    result = await menuai.config_entries.flow.async_init(
        "test", context={"source": config_entries.SOURCE_DISCOVERY}, data={}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    flow = next(
        (
            flw
            for flw in menuai.config_entries.flow.async_progress()
            if flw["flow_id"] == result["flow_id"]
        ),
        None,
    )

    # Ignore it.
    await menuai.config_entries.flow.async_init(
        flow["handler"],
        context={"source": config_entries.SOURCE_IGNORE},
        data={"unique_id": flow["context"]["unique_id"], "title": "Ignored Entry"},
    )

    # Second discovery should be aborted
    result = await menuai.config_entries.flow.async_init(
        "test", context={"source": config_entries.SOURCE_DISCOVERY}, data={}
    )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT


async def test_webhook_single_entry_allowed(
    menuai: menuai, webhook_flow_conf: None
) -> None:
    """Test only a single entry is allowed."""
    flow = config_entries.HANDLERS["test_single"]()
    flow.menuai = menuai

    MockConfigEntry(domain="test_single").add_to_menuai(menuai)
    result = await flow.async_step_user()

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_webhook_multiple_entries_allowed(
    menuai: menuai, webhook_flow_conf: None
) -> None:
    """Test multiple entries are allowed when specified."""
    flow = config_entries.HANDLERS["test_multiple"]()
    flow.menuai = menuai

    MockConfigEntry(domain="test_multiple").add_to_menuai(menuai)
    menuai.config.api = Mock(base_url="http://example.com")

    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.FlowResultType.FORM


async def test_webhook_config_flow_registers_webhook(
    menuai: menuai, webhook_flow_conf: None
) -> None:
    """Test setting up an entry creates a webhook."""
    flow = config_entries.HANDLERS["test_single"]()
    flow.menuai = menuai

    await async_process_ha_core_config(
        menuai,
        {"external_url": "https://example.com"},
    )
    result = await flow.async_step_user(user_input={})

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"]["webhook_id"] is not None


async def test_webhook_create_cloudhook(
    menuai: menuai, webhook_flow_conf: None
) -> None:
    """Test cloudhook will be created if subscribed."""
    assert await setup.async_setup_component(menuai, "cloud", {})

    async_setup_entry = Mock(return_value=True)
    async_unload_entry = Mock(return_value=True)

    mock_integration(
        menuai,
        MockModule(
            "test_single",
            async_setup_entry=async_setup_entry,
            async_unload_entry=async_unload_entry,
            async_remove_entry=config_entry_flow.webhook_async_remove_entry,
        ),
    )
    mock_platform(menuai, "test_single.config_flow", None)

    result = await menuai.config_entries.flow.async_init(
        "test_single", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    with (
        patch(
            "menuai_nabucasa.cloudhooks.Cloudhooks.async_create",
            return_value={"cloudhook_url": "https://example.com"},
        ) as mock_create,
        patch(
            "menuai_nabucasa.Cloud.subscription_expired",
            new_callable=PropertyMock(return_value=False),
        ),
        patch(
            "menuai_nabucasa.Cloud.is_logged_in",
            new_callable=PropertyMock(return_value=True),
        ),
        patch(
            "menuai_nabucasa.iot_base.BaseIoT.connected",
            new_callable=PropertyMock(return_value=True),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["description_placeholders"]["webhook_url"] == "https://example.com"
    assert len(mock_create.mock_calls) == 1
    assert len(async_setup_entry.mock_calls) == 1

    with patch(
        "menuai_nabucasa.cloudhooks.Cloudhooks.async_delete",
        return_value={"cloudhook_url": "https://example.com"},
    ) as mock_delete:
        result = await menuai.config_entries.async_remove(result["result"].entry_id)

    assert len(mock_delete.mock_calls) == 1
    assert result["require_restart"] is False
    await menuai.async_block_till_done()


async def test_webhook_create_cloudhook_aborts_not_connected(
    menuai: menuai, webhook_flow_conf: None
) -> None:
    """Test cloudhook aborts if subscribed but not connected."""
    assert await setup.async_setup_component(menuai, "cloud", {})

    async_setup_entry = Mock(return_value=True)
    async_unload_entry = Mock(return_value=True)

    mock_integration(
        menuai,
        MockModule(
            "test_single",
            async_setup_entry=async_setup_entry,
            async_unload_entry=async_unload_entry,
            async_remove_entry=config_entry_flow.webhook_async_remove_entry,
        ),
    )
    mock_platform(menuai, "test_single.config_flow", None)

    result = await menuai.config_entries.flow.async_init(
        "test_single", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    with (
        patch(
            "menuai_nabucasa.cloudhooks.Cloudhooks.async_create",
            return_value={"cloudhook_url": "https://example.com"},
        ),
        patch(
            "menuai_nabucasa.Cloud.subscription_expired",
            new_callable=PropertyMock(return_value=False),
        ),
        patch(
            "menuai_nabucasa.Cloud.is_logged_in",
            new_callable=PropertyMock(return_value=True),
        ),
        patch(
            "menuai_nabucasa.iot_base.BaseIoT.connected",
            new_callable=PropertyMock(return_value=False),
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "cloud_not_connected"
