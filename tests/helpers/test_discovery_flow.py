"""Test the discovery flow helper."""

from collections.abc import Generator
from unittest.mock import AsyncMock, call, patch

import pytest

from menuai import config_entries
from menuai.const import EVENT_menuai_STARTED
from menuai.core import CoreState, menuai
from menuai.helpers import discovery_flow, json as json_helper
from menuai.helpers.discovery_flow import DiscoveryKey


@pytest.fixture
def mock_flow_init(menuai: menuai) -> Generator[AsyncMock]:
    """Mock menuai.config_entries.flow.async_init."""
    with patch.object(
        menuai.config_entries.flow, "async_init", return_value=AsyncMock()
    ) as mock_init:
        yield mock_init


@pytest.mark.parametrize(
    ("discovery_key", "context"),
    [
        (None, {}),
        (
            DiscoveryKey(domain="test", key="string_key", version=1),
            {"discovery_key": DiscoveryKey(domain="test", key="string_key", version=1)},
        ),
        (
            DiscoveryKey(domain="test", key=("one", "two"), version=1),
            {
                "discovery_key": DiscoveryKey(
                    domain="test", key=("one", "two"), version=1
                )
            },
        ),
    ],
)
async def test_async_create_flow(
    menuai: menuai,
    mock_flow_init: AsyncMock,
    discovery_key: DiscoveryKey | None,
    context: {},
) -> None:
    """Test we can create a flow."""
    discovery_flow.async_create_flow(
        menuai,
        "hue",
        {"source": config_entries.SOURCE_HOMEKIT},
        {"properties": {"id": "aa:bb:cc:dd:ee:ff"}},
        discovery_key=discovery_key,
    )
    assert mock_flow_init.mock_calls == [
        call(
            "hue",
            context={"source": "homekit"} | context,
            data={"properties": {"id": "aa:bb:cc:dd:ee:ff"}},
        )
    ]


async def test_async_create_flow_deferred_until_started(
    menuai: menuai, mock_flow_init: AsyncMock
) -> None:
    """Test flows are deferred until started."""
    menuai.set_state(CoreState.stopped)
    discovery_flow.async_create_flow(
        menuai,
        "hue",
        {"source": config_entries.SOURCE_HOMEKIT},
        {"properties": {"id": "aa:bb:cc:dd:ee:ff"}},
    )
    assert not mock_flow_init.mock_calls
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()
    assert mock_flow_init.mock_calls == [
        call(
            "hue",
            context={"source": "homekit"},
            data={"properties": {"id": "aa:bb:cc:dd:ee:ff"}},
        )
    ]


async def test_async_create_flow_checks_existing_flows_after_startup(
    menuai: menuai, mock_flow_init: AsyncMock
) -> None:
    """Test existing flows prevent an identical ones from being after startup."""
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    with patch(
        "menuai.config_entries.ConfigEntriesFlowManager.async_has_matching_discovery_flow",
        return_value=True,
    ):
        discovery_flow.async_create_flow(
            menuai,
            "hue",
            {"source": config_entries.SOURCE_HOMEKIT},
            {"properties": {"id": "aa:bb:cc:dd:ee:ff"}},
        )
        assert not mock_flow_init.mock_calls


async def test_async_create_flow_checks_existing_flows_before_startup(
    menuai: menuai, mock_flow_init: AsyncMock
) -> None:
    """Test existing flows prevent an identical ones from being created before startup."""
    menuai.set_state(CoreState.stopped)
    for _ in range(2):
        discovery_flow.async_create_flow(
            menuai,
            "hue",
            {"source": config_entries.SOURCE_HOMEKIT},
            {"properties": {"id": "aa:bb:cc:dd:ee:ff"}},
        )
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()
    assert mock_flow_init.mock_calls == [
        call(
            "hue",
            context={"source": "homekit"},
            data={"properties": {"id": "aa:bb:cc:dd:ee:ff"}},
        )
    ]


async def test_async_create_flow_does_nothing_after_stop(
    menuai: menuai, mock_flow_init: AsyncMock
) -> None:
    """Test we no longer create flows when menuai is stopping."""
    menuai.bus.async_fire(EVENT_menuai_STARTED)
    await menuai.async_block_till_done()
    menuai.set_state(CoreState.stopping)
    mock_flow_init.reset_mock()
    discovery_flow.async_create_flow(
        menuai,
        "hue",
        {"source": config_entries.SOURCE_HOMEKIT},
        {"properties": {"id": "aa:bb:cc:dd:ee:ff"}},
    )
    assert len(mock_flow_init.mock_calls) == 0


@pytest.mark.parametrize("key", ["test", ("blah", "bleh")])
def test_discovery_key_serialize_deserialize(key: str | tuple[str]) -> None:
    """Test serialize and deserialize discovery key."""
    discovery_key_1 = discovery_flow.DiscoveryKey(
        domain="test_domain", key=key, version=1
    )
    serialized = json_helper.json_dumps(discovery_key_1)
    assert (
        discovery_flow.DiscoveryKey.from_json_dict(json_helper.json_loads(serialized))
        == discovery_key_1
    )
