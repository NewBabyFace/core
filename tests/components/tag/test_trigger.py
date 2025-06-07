"""Tests for tag triggers."""

from typing import Any

import pytest

from menuai.components import automation
from menuai.components.tag import async_scan_tag
from menuai.components.tag.const import DEVICE_ID, DOMAIN, TAG_ID
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF
from menuai.core import menuai, ServiceCall
from menuai.setup import async_setup_component


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


@pytest.fixture
def tag_setup(menuai: menuai, menuai_storage: dict[str, Any]):
    """Tag setup."""

    async def _storage(items=None):
        if items is None:
            menuai_storage[DOMAIN] = {
                "key": DOMAIN,
                "version": 1,
                "minor_version": 2,
                "data": {"items": [{"id": "test tag", "tag_id": "test tag"}]},
            }
        else:
            menuai_storage[DOMAIN] = items
        config = {DOMAIN: {}}
        return await async_setup_component(menuai, DOMAIN, config)

    return _storage


async def test_triggers(
    menuai: menuai, tag_setup, service_calls: list[ServiceCall]
) -> None:
    """Test tag triggers."""
    assert await tag_setup()
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "alias": "test",
                    "trigger": {"platform": DOMAIN, TAG_ID: "abc123"},
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "message": "service called",
                            "id": "{{ trigger.id}}",
                        },
                    },
                }
            ]
        },
    )

    await menuai.async_block_till_done()

    await async_scan_tag(menuai, "abc123", None)
    await menuai.async_block_till_done()

    assert len(service_calls) == 1
    assert service_calls[0].data["message"] == "service called"
    assert service_calls[0].data["id"] == 0

    await menuai.services.async_call(
        automation.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "automation.test"},
        blocking=True,
    )
    assert len(service_calls) == 2

    await async_scan_tag(menuai, "abc123", None)
    await menuai.async_block_till_done()

    assert len(service_calls) == 2


async def test_exception_bad_trigger(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test for exception on event triggers firing."""

    await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {"trigger": {"platform": DOMAIN, "oops": "abc123"}},
                    "action": {
                        "service": "test.automation",
                        "data": {"message": "service called"},
                    },
                }
            ]
        },
    )
    await menuai.async_block_till_done()
    assert "Unnamed automation could not be validated" in caplog.text


async def test_multiple_tags_and_devices_trigger(
    menuai: menuai, tag_setup, service_calls: list[ServiceCall]
) -> None:
    """Test multiple tags and devices triggers."""
    assert await tag_setup()
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": DOMAIN,
                        TAG_ID: ["abc123", "def456"],
                        DEVICE_ID: ["ghi789", "jkl0123"],
                    },
                    "action": {
                        "service": "test.automation",
                        "data": {"message": "service called"},
                    },
                }
            ]
        },
    )

    await menuai.async_block_till_done()

    # Should not trigger
    await async_scan_tag(menuai, tag_id="abc123", device_id=None)
    await async_scan_tag(menuai, tag_id="abc123", device_id="invalid")
    await menuai.async_block_till_done()

    # Should trigger
    await async_scan_tag(menuai, tag_id="abc123", device_id="ghi789")
    await menuai.async_block_till_done()
    await async_scan_tag(menuai, tag_id="abc123", device_id="jkl0123")
    await menuai.async_block_till_done()
    await async_scan_tag(menuai, "def456", device_id="ghi789")
    await menuai.async_block_till_done()
    await async_scan_tag(menuai, "def456", device_id="jkl0123")
    await menuai.async_block_till_done()

    assert len(service_calls) == 4
    assert service_calls[0].data["message"] == "service called"
    assert service_calls[1].data["message"] == "service called"
    assert service_calls[2].data["message"] == "service called"
    assert service_calls[3].data["message"] == "service called"
