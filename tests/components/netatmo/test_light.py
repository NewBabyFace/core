"""The tests for Netatmo light."""

from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.light import (
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.components.netatmo import DOMAIN
from menuai.const import ATTR_ENTITY_ID, CONF_WEBHOOK_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import (
    FAKE_WEBHOOK_ACTIVATION,
    selected_platforms,
    simulate_webhook,
    snapshot_platform_entities,
)

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMockResponse


async def test_entity(
    menuai: menuai,
    config_entry: MockConfigEntry,
    netatmo_auth: AsyncMock,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test entities."""
    await snapshot_platform_entities(
        menuai,
        config_entry,
        Platform.LIGHT,
        entity_registry,
        snapshot,
    )


async def test_camera_light_setup_and_services(
    menuai: menuai, config_entry: MockConfigEntry, netatmo_auth: AsyncMock
) -> None:
    """Test camera ligiht setup and services."""
    with selected_platforms(["light"]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)

        await menuai.async_block_till_done()

    webhook_id = config_entry.data[CONF_WEBHOOK_ID]

    # Fake webhook activation
    await simulate_webhook(menuai, webhook_id, FAKE_WEBHOOK_ACTIVATION)
    await menuai.async_block_till_done()

    light_entity = "light.front"
    assert menuai.states.get(light_entity).state == "unavailable"

    # Trigger light mode change
    response = {
        "event_type": "light_mode",
        "device_id": "12:34:56:10:b9:0e",
        "camera_id": "12:34:56:10:b9:0e",
        "event_id": "601dce1560abca1ebad9b723",
        "push_type": "NOC-light_mode",
        "sub_type": "on",
    }
    await simulate_webhook(menuai, webhook_id, response)

    assert menuai.states.get(light_entity).state == "on"

    # Trigger light mode change with erroneous webhook data
    response = {
        "event_type": "light_mode",
        "device_id": "12:34:56:10:b9:0e",
    }
    await simulate_webhook(menuai, webhook_id, response)

    assert menuai.states.get(light_entity).state == "on"

    # Test turning light off
    with patch("pyatmo.home.Home.async_set_state") as mock_set_state:
        await menuai.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: light_entity},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once_with(
            {"modules": [{"id": "12:34:56:10:b9:0e", "floodlight": "auto"}]}
        )

    # Test turning light on
    with patch("pyatmo.home.Home.async_set_state") as mock_set_state:
        await menuai.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: light_entity},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once_with(
            {"modules": [{"id": "12:34:56:10:b9:0e", "floodlight": "on"}]}
        )


async def test_setup_component_no_devices(menuai: menuai, config_entry) -> None:
    """Test setup with no devices."""
    fake_post_hits = 0

    async def fake_post_request_no_data(*args, **kwargs):
        """Fake error during requesting backend data."""
        nonlocal fake_post_hits
        fake_post_hits += 1
        return AiohttpClientMockResponse(
            method="POST",
            url=kwargs["endpoint"],
            json={},
        )

    with (
        patch(
            "menuai.components.netatmo.api.AsyncConfigEntryNetatmoAuth"
        ) as mock_auth,
        patch("menuai.components.netatmo.data_handler.PLATFORMS", ["light"]),
        patch(
            "menuai.helpers.config_entry_oauth2_flow.async_get_config_entry_implementation",
        ),
        patch(
            "menuai.components.netatmo.webhook_generate_url",
        ),
    ):
        mock_auth.return_value.async_post_api_request.side_effect = (
            fake_post_request_no_data
        )
        mock_auth.return_value.async_addwebhook.side_effect = AsyncMock()
        mock_auth.return_value.async_dropwebhook.side_effect = AsyncMock()

        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        # Fake webhook activation
        await simulate_webhook(
            menuai, config_entry.data[CONF_WEBHOOK_ID], FAKE_WEBHOOK_ACTIVATION
        )
        await menuai.async_block_till_done()

        assert fake_post_hits == 3

        assert menuai.config_entries.async_entries(DOMAIN)
        assert len(menuai.states.async_all()) == 0


async def test_light_setup_and_services(
    menuai: menuai, config_entry: MockConfigEntry, netatmo_auth: AsyncMock
) -> None:
    """Test setup and services."""
    with selected_platforms(["light"]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)

        await menuai.async_block_till_done()

    light_entity = "light.bathroom_light"

    assert menuai.states.get(light_entity).state == "off"

    # Test turning light off
    with patch("pyatmo.home.Home.async_set_state") as mock_set_state:
        await menuai.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: light_entity},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once_with(
            {
                "modules": [
                    {
                        "id": "12:34:56:00:01:01:01:a1",
                        "on": False,
                        "bridge": "12:34:56:80:60:40",
                    }
                ]
            }
        )

    # Test turning light on
    with patch("pyatmo.home.Home.async_set_state") as mock_set_state:
        await menuai.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: light_entity},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once_with(
            {
                "modules": [
                    {
                        "id": "12:34:56:00:01:01:01:a1",
                        "on": True,
                        "bridge": "12:34:56:80:60:40",
                    }
                ]
            }
        )
