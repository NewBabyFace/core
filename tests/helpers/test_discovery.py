"""Test discovery helpers."""

from unittest.mock import patch

import pytest

from menuai import setup
from menuai.const import Platform
from menuai.core import menuai, callback
from menuai.helpers import discovery
from menuai.helpers.dispatcher import async_dispatcher_send
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from tests.common import MockModule, MockPlatform, mock_integration, mock_platform


@pytest.fixture
def mock_setup_component():
    """Mock setup component."""
    with patch("menuai.setup.async_setup_component", return_value=True) as mock:
        yield mock


async def test_listen(menuai: menuai, mock_setup_component) -> None:
    """Test discovery listen/discover combo."""
    calls_single = []

    @callback
    def callback_single(service, info):
        """Service discovered callback."""
        calls_single.append((service, info))

    discovery.async_listen(menuai, "test service", callback_single)

    await discovery.async_discover(
        menuai,
        "test service",
        "discovery info",
        "test_component",
        {},
    )
    await menuai.async_block_till_done()

    assert mock_setup_component.called
    assert mock_setup_component.call_args[0] == (menuai, "test_component", {})
    assert len(calls_single) == 1
    assert calls_single[0] == ("test service", "discovery info")


async def test_platform(menuai: menuai, mock_setup_component) -> None:
    """Test discover platform method."""
    calls = []

    @callback
    def platform_callback(platform, info):
        """Platform callback method."""
        calls.append((platform, info))

    discovery.async_listen_platform(
        menuai,
        "test_component",
        platform_callback,
    )

    await discovery.async_load_platform(
        menuai,
        "test_component",
        "test_platform",
        "discovery info",
        {"test_component": {}},
    )
    await menuai.async_block_till_done()
    assert mock_setup_component.called
    assert mock_setup_component.call_args[0] == (
        menuai,
        "test_component",
        {"test_component": {}},
    )
    await menuai.async_block_till_done()

    await menuai.async_add_executor_job(
        discovery.load_platform,
        menuai,
        "test_component_2",
        "test_platform",
        "discovery info",
        {"test_component": {}},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0] == ("test_platform", "discovery info")

    async_dispatcher_send(
        menuai,
        discovery.SIGNAL_PLATFORM_DISCOVERED,
        {"service": discovery.EVENT_LOAD_PLATFORM.format("test_component")},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1


async def test_circular_import(menuai: menuai) -> None:
    """Test we don't break doing circular import.

    This test will have test_component discover the switch.test_circular
    component while setting up.

    The supplied config will load test_component and will load
    switch.test_circular.

    That means that after startup, we will have test_component and switch
    setup. The test_circular platform has been loaded twice.
    """
    component_calls = []
    platform_calls = []

    def component_setup(menuai: menuai, config: ConfigType) -> bool:
        """Set up mock component."""
        discovery.load_platform(
            menuai, Platform.SWITCH, "test_circular", {"key": "value"}, config
        )
        component_calls.append(1)
        return True

    def setup_platform(
        menuai: menuai,
        config: ConfigType,
        add_entities_callback: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None,
    ) -> None:
        """Set up mock platform."""
        platform_calls.append("disc" if discovery_info else "component")

    mock_integration(menuai, MockModule("test_component", setup=component_setup))

    # dependencies are only set in component level
    # since we are using manifest to hold them
    mock_integration(menuai, MockModule("test_circular", dependencies=["test_component"]))
    mock_platform(
        menuai, "test_circular.switch", MockPlatform(setup_platform=setup_platform)
    )

    await setup.async_setup_component(
        menuai,
        "test_component",
        {"test_component": None, "switch": [{"platform": "test_circular"}]},
    )

    await menuai.async_block_till_done()

    # test_component will only be setup once
    assert len(component_calls) == 1
    # The platform will be setup once via the config in `setup_component`
    # and once via the discovery inside test_component.
    assert len(platform_calls) == 2
    assert "test_component" in menuai.config.components
    assert "switch" in menuai.config.components


async def test_1st_discovers_2nd_component(menuai: menuai) -> None:
    """Test that we don't break if one component discovers the other.

    If the first component fires a discovery event to set up the
    second component while the second component is about to be set up,
    it should not set up the second component twice.
    """
    component_calls = []

    async def component1_setup(menuai: menuai, config: ConfigType) -> bool:
        """Set up mock component."""
        await discovery.async_discover(
            menuai, "test_component2", {}, "test_component2", {}
        )
        return True

    def component2_setup(menuai: menuai, config: ConfigType) -> bool:
        """Set up mock component."""
        component_calls.append(1)
        return True

    mock_integration(menuai, MockModule("test_component1", async_setup=component1_setup))

    mock_integration(menuai, MockModule("test_component2", setup=component2_setup))

    menuai.async_create_task(setup.async_setup_component(menuai, "test_component1", {}))
    menuai.async_create_task(setup.async_setup_component(menuai, "test_component2", {}))
    await menuai.async_block_till_done()

    # test_component will only be setup once
    assert len(component_calls) == 1
