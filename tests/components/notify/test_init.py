"""The tests for notify entity platform."""

import copy
from unittest.mock import MagicMock

import pytest
import voluptuous as vol

from menuai.components import notify
from menuai.components.notify import (
    DOMAIN,
    SERVICE_SEND_MESSAGE,
    NotifyEntity,
    NotifyEntityDescription,
    NotifyEntityFeature,
)
from menuai.config_entries import ConfigEntry
from menuai.const import STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from menuai.core import menuai, State

from tests.common import (
    MockConfigEntry,
    MockEntity,
    MockModule,
    mock_integration,
    mock_platform,
    mock_restore_cache,
    setup_test_component_platform,
)

TEST_KWARGS = {notify.ATTR_MESSAGE: "Test message"}
TEST_KWARGS_TITLE = {notify.ATTR_MESSAGE: "Test message", notify.ATTR_TITLE: "My title"}


class MockNotifyEntity(MockEntity, NotifyEntity):
    """Mock Email notitier entity to use in tests."""

    send_message_mock_calls = MagicMock()

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send a notification message."""
        self.send_message_mock_calls(message, title=title)


class MockNotifyEntityNonAsync(MockEntity, NotifyEntity):
    """Mock Email notitier entity to use in tests."""

    send_message_mock_calls = MagicMock()

    def send_message(self, message: str, title: str | None = None) -> None:
        """Send a notification message."""
        self.send_message_mock_calls(message, title=title)


async def help_async_setup_entry_init(
    menuai: menuai, config_entry: ConfigEntry
) -> bool:
    """Set up test config entry."""
    await menuai.config_entries.async_forward_entry_setups(
        config_entry, [Platform.NOTIFY]
    )
    return True


async def help_async_unload_entry(
    menuai: menuai, config_entry: ConfigEntry
) -> bool:
    """Unload test config emntry."""
    return await menuai.config_entries.async_unload_platforms(
        config_entry, [Platform.NOTIFY]
    )


@pytest.mark.parametrize(
    "entity",
    [
        MockNotifyEntityNonAsync(name="test", entity_id="notify.test"),
        MockNotifyEntity(name="test", entity_id="notify.test"),
    ],
    ids=["non_async", "async"],
)
async def test_send_message_service(
    menuai: menuai, config_flow_fixture: None, entity: NotifyEntity
) -> None:
    """Test send_message service."""

    config_entry = MockConfigEntry(domain="test")
    config_entry.add_to_menuai(menuai)

    mock_integration(
        menuai,
        MockModule(
            "test",
            async_setup_entry=help_async_setup_entry_init,
            async_unload_entry=help_async_unload_entry,
        ),
    )
    setup_test_component_platform(menuai, DOMAIN, [entity], from_config_entry=True)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    state = menuai.states.get("notify.test")
    assert state.state is STATE_UNKNOWN

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SEND_MESSAGE,
        copy.deepcopy(TEST_KWARGS) | {"entity_id": "notify.test"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    entity.send_message_mock_calls.assert_called_once()
    entity.send_message_mock_calls.reset_mock()

    # Test schema: `None` message fails
    with pytest.raises(vol.Invalid) as exc:
        await menuai.services.async_call(
            notify.DOMAIN,
            notify.SERVICE_SEND_MESSAGE,
            {"entity_id": "notify.test", notify.ATTR_MESSAGE: None},
        )
    assert (
        str(exc.value) == "string value is None for dictionary value @ data['message']"
    )
    entity.send_message_mock_calls.assert_not_called()

    # Test schema: No message fails
    with pytest.raises(vol.Invalid) as exc:
        await menuai.services.async_call(
            notify.DOMAIN, notify.SERVICE_SEND_MESSAGE, {"entity_id": "notify.test"}
        )
    assert str(exc.value) == "required key not provided @ data['message']"
    entity.send_message_mock_calls.assert_not_called()

    # Test unloading the entry succeeds
    assert await menuai.config_entries.async_unload(config_entry.entry_id)


@pytest.mark.parametrize(
    "entity",
    [
        MockNotifyEntityNonAsync(
            name="test",
            entity_id="notify.test",
            supported_features=NotifyEntityFeature.TITLE,
        ),
        MockNotifyEntity(
            name="test",
            entity_id="notify.test",
            supported_features=NotifyEntityFeature.TITLE,
        ),
    ],
    ids=["non_async", "async"],
)
async def test_send_message_service_with_title(
    menuai: menuai, config_flow_fixture: None, entity: NotifyEntity
) -> None:
    """Test send_message service."""

    config_entry = MockConfigEntry(domain="test")
    config_entry.add_to_menuai(menuai)

    mock_integration(
        menuai,
        MockModule(
            "test",
            async_setup_entry=help_async_setup_entry_init,
            async_unload_entry=help_async_unload_entry,
        ),
    )
    setup_test_component_platform(menuai, DOMAIN, [entity], from_config_entry=True)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    state = menuai.states.get("notify.test")
    assert state.state is STATE_UNKNOWN

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SEND_MESSAGE,
        copy.deepcopy(TEST_KWARGS_TITLE) | {"entity_id": "notify.test"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    entity.send_message_mock_calls.assert_called_once_with(
        TEST_KWARGS_TITLE[notify.ATTR_MESSAGE],
        title=TEST_KWARGS_TITLE[notify.ATTR_TITLE],
    )


@pytest.mark.parametrize(
    ("state", "init_state"),
    [
        ("2021-01-01T23:59:59+00:00", "2021-01-01T23:59:59+00:00"),
        (STATE_UNAVAILABLE, STATE_UNKNOWN),
    ],
)
async def test_restore_state(
    menuai: menuai, config_flow_fixture: None, state: str, init_state: str
) -> None:
    """Test we restore state integration."""
    mock_restore_cache(menuai, (State("notify.test", state),))

    mock_integration(
        menuai,
        MockModule(
            "test",
            async_setup_entry=help_async_setup_entry_init,
        ),
    )

    entity = MockNotifyEntity(name="test", entity_id="notify.test")
    setup_test_component_platform(menuai, DOMAIN, [entity], from_config_entry=True)

    config_entry = MockConfigEntry(domain="test")
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    state = menuai.states.get("notify.test")
    assert state is not None
    assert state.state is init_state


async def test_name(menuai: menuai, config_flow_fixture: None) -> None:
    """Test notify name."""

    mock_platform(menuai, "test.config_flow")
    mock_integration(
        menuai,
        MockModule(
            "test",
            async_setup_entry=help_async_setup_entry_init,
        ),
    )

    # Unnamed notify entity -> no name
    entity1 = NotifyEntity()
    entity1.entity_id = "notify.test1"

    # Unnamed notify entity and has_entity_name True -> unnamed
    entity2 = NotifyEntity()
    entity2.entity_id = "notify.test3"
    entity2._attr_has_entity_name = True

    # Named notify entity and has_entity_name True -> named
    entity3 = NotifyEntity()
    entity3.entity_id = "notify.test4"
    entity3.entity_description = NotifyEntityDescription("test", has_entity_name=True)

    setup_test_component_platform(
        menuai, DOMAIN, [entity1, entity2, entity3], from_config_entry=True
    )

    config_entry = MockConfigEntry(domain="test")
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get(entity1.entity_id)
    assert state
    assert state.attributes == {"supported_features": NotifyEntityFeature(0)}

    state = menuai.states.get(entity2.entity_id)
    assert state
    assert state.attributes == {"supported_features": NotifyEntityFeature(0)}

    state = menuai.states.get(entity3.entity_id)
    assert state
    assert state.attributes == {"supported_features": NotifyEntityFeature(0)}
