"""The tests for the webhook automation trigger."""

from ipaddress import ip_address
from unittest.mock import Mock, patch

import pytest

from menuai.core import menuai, callback
from menuai.setup import async_setup_component

from tests.typing import ClientSessionGenerator


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


@pytest.fixture(autouse=True)
async def setup_http(menuai: menuai) -> None:
    """Set up http."""
    assert await async_setup_component(menuai, "http", {})
    assert await async_setup_component(menuai, "webhook", {})
    await menuai.async_block_till_done()


async def test_webhook_json(
    menuai: menuai, menuai_client_no_auth: ClientSessionGenerator
) -> None:
    """Test triggering with a JSON webhook."""
    events = []

    @callback
    def store_event(event):
        """Help store events."""
        events.append(event)

    menuai.bus.async_listen("test_success", store_event)

    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": {
                "trigger": {"platform": "webhook", "webhook_id": "json_webhook"},
                "action": {
                    "event": "test_success",
                    "event_data_template": {
                        "hello": "yo {{ trigger.json.hello }}",
                        "id": "{{ trigger.id}}",
                    },
                },
            }
        },
    )
    await menuai.async_block_till_done()

    client = await menuai_client_no_auth()

    await client.post("/api/webhook/json_webhook", json={"hello": "world"})
    await menuai.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["hello"] == "yo world"
    assert events[0].data["id"] == 0


async def test_webhook_post(
    menuai: menuai, menuai_client_no_auth: ClientSessionGenerator
) -> None:
    """Test triggering with a POST webhook."""
    # Set up fake cloud
    menuai.config.components.add("cloud")

    events = []

    @callback
    def store_event(event):
        """Help store events."""
        events.append(event)

    menuai.bus.async_listen("test_success", store_event)

    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": {
                "trigger": {
                    "platform": "webhook",
                    "webhook_id": "post_webhook",
                    "local_only": True,
                },
                "action": {
                    "event": "test_success",
                    "event_data_template": {"hello": "yo {{ trigger.data.hello }}"},
                },
            }
        },
    )
    await menuai.async_block_till_done()

    client = await menuai_client_no_auth()

    await client.post("/api/webhook/post_webhook", data={"hello": "world"})
    await menuai.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["hello"] == "yo world"

    # Request from remote IP
    with patch(
        "menuai.components.webhook.ip_address",
        return_value=ip_address("123.123.123.123"),
    ):
        await client.post("/api/webhook/post_webhook", data={"hello": "world"})
    # No hook received
    await menuai.async_block_till_done()
    assert len(events) == 1

    # Request from MenuAI Cloud remote UI
    with patch(
        "menuai_nabucasa.remote.is_cloud_request", Mock(get=Mock(return_value=True))
    ):
        await client.post("/api/webhook/post_webhook", data={"hello": "world"})

    # No hook received
    await menuai.async_block_till_done()
    assert len(events) == 1


async def test_webhook_allowed_methods_internet(
    menuai: menuai, menuai_client_no_auth: ClientSessionGenerator
) -> None:
    """Test the webhook obeys allowed_methods and local_only options."""
    events = []

    @callback
    def store_event(event):
        """Help store events."""
        events.append(event)

    menuai.bus.async_listen("test_success", store_event)

    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": {
                "trigger": {
                    "platform": "webhook",
                    "webhook_id": "post_webhook",
                    "allowed_methods": "PUT",
                    "local_only": False,
                },
                "action": {
                    "event": "test_success",
                },
            }
        },
    )
    await menuai.async_block_till_done()

    client = await menuai_client_no_auth()

    await client.post("/api/webhook/post_webhook")
    await menuai.async_block_till_done()

    assert len(events) == 0

    # Request from remote IP
    with patch(
        "menuai.components.webhook.ip_address",
        return_value=ip_address("123.123.123.123"),
    ):
        await client.put("/api/webhook/post_webhook")
    await menuai.async_block_till_done()
    assert len(events) == 1


async def test_webhook_query(
    menuai: menuai, menuai_client_no_auth: ClientSessionGenerator
) -> None:
    """Test triggering with a query POST webhook."""
    events = []

    @callback
    def store_event(event):
        """Help store events."""
        events.append(event)

    menuai.bus.async_listen("test_success", store_event)

    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": {
                "trigger": {"platform": "webhook", "webhook_id": "query_webhook"},
                "action": {
                    "event": "test_success",
                    "event_data_template": {"hello": "yo {{ trigger.query.hello }}"},
                },
            }
        },
    )
    await menuai.async_block_till_done()

    client = await menuai_client_no_auth()

    await client.post("/api/webhook/query_webhook?hello=world")
    await menuai.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["hello"] == "yo world"


async def test_webhook_multiple(
    menuai: menuai, menuai_client_no_auth: ClientSessionGenerator
) -> None:
    """Test triggering multiple triggers with a POST webhook."""
    events1 = []
    events2 = []

    @callback
    def store_event1(event):
        """Help store events."""
        events1.append(event)

    @callback
    def store_event2(event):
        """Help store events."""
        events2.append(event)

    menuai.bus.async_listen("test_success1", store_event1)
    menuai.bus.async_listen("test_success2", store_event2)

    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": [
                {
                    "trigger": {"platform": "webhook", "webhook_id": "post_webhook"},
                    "action": {
                        "event": "test_success1",
                        "event_data_template": {"hello": "yo {{ trigger.data.hello }}"},
                    },
                },
                {
                    "trigger": {"platform": "webhook", "webhook_id": "post_webhook"},
                    "action": {
                        "event": "test_success2",
                        "event_data_template": {
                            "hello": "yo2 {{ trigger.data.hello }}"
                        },
                    },
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    client = await menuai_client_no_auth()

    await client.post("/api/webhook/post_webhook", data={"hello": "world"})
    await menuai.async_block_till_done()

    assert len(events1) == 1
    assert events1[0].data["hello"] == "yo world"
    assert len(events2) == 1
    assert events2[0].data["hello"] == "yo2 world"


async def test_webhook_reload(
    menuai: menuai, menuai_client_no_auth: ClientSessionGenerator
) -> None:
    """Test reloading a webhook."""
    events = []

    @callback
    def store_event(event):
        """Help store events."""
        events.append(event)

    menuai.bus.async_listen("test_success", store_event)

    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": {
                "trigger": {"platform": "webhook", "webhook_id": "post_webhook"},
                "action": {
                    "event": "test_success",
                    "event_data_template": {"hello": "yo {{ trigger.data.hello }}"},
                },
            }
        },
    )
    await menuai.async_block_till_done()

    client = await menuai_client_no_auth()

    await client.post("/api/webhook/post_webhook", data={"hello": "world"})
    await menuai.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["hello"] == "yo world"

    with patch(
        "menuai.config.load_yaml_config_file",
        autospec=True,
        return_value={
            "automation": {
                "trigger": {"platform": "webhook", "webhook_id": "post_webhook"},
                "action": {
                    "event": "test_success",
                    "event_data_template": {"hello": "yo2 {{ trigger.data.hello }}"},
                },
            }
        },
    ):
        await menuai.services.async_call(
            "automation",
            "reload",
            blocking=True,
        )
        await menuai.async_block_till_done()

    await client.post("/api/webhook/post_webhook", data={"hello": "world"})
    await menuai.async_block_till_done()

    assert len(events) == 2
    assert events[1].data["hello"] == "yo2 world"
