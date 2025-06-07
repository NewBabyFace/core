"""Test the Matter helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from matter_server.client.models.node import MatterNode
import pytest

from menuai.components.matter.const import DOMAIN
from menuai.components.matter.helpers import (
    get_device_id,
    get_node_from_device_entry,
)
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .common import setup_integration_with_node_fixture

from tests.common import MockConfigEntry


@pytest.mark.parametrize("node_fixture", ["device_diagnostics"])
async def test_get_device_id(
    menuai: menuai,
    matter_client: MagicMock,
    matter_node: MatterNode,
) -> None:
    """Test get_device_id."""
    device_id = get_device_id(matter_client.server_info, matter_node.endpoints[0])

    assert device_id == "00000000000004D2-0000000000000005-MatterNodeDevice"


async def test_get_node_from_device_entry(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    matter_client: MagicMock,
) -> None:
    """Test get_node_from_device_entry."""
    other_domain = "other_domain"
    other_config_entry = MockConfigEntry(domain=other_domain)
    other_config_entry.add_to_menuai(menuai)
    other_device_entry = device_registry.async_get_or_create(
        config_entry_id=other_config_entry.entry_id,
        identifiers={(other_domain, "1234")},
    )
    node = await setup_integration_with_node_fixture(
        menuai, "device_diagnostics", matter_client
    )
    config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    device_entry = dr.async_entries_for_config_entry(
        device_registry, config_entry.entry_id
    )[0]
    assert device_entry
    node_from_device_entry = get_node_from_device_entry(menuai, device_entry)

    assert node_from_device_entry is node

    # test non-Matter device returns None
    assert get_node_from_device_entry(menuai, other_device_entry) is None

    matter_client.server_info = None

    # test non-initialized server raises RuntimeError
    with pytest.raises(RuntimeError) as runtime_error:
        node_from_device_entry = get_node_from_device_entry(menuai, device_entry)

    assert "Matter server information is not available" in str(runtime_error.value)
