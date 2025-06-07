"""Test event helpers."""

import asyncio
from collections.abc import Callable
import contextlib
from datetime import date, datetime, timedelta
from unittest.mock import patch

from astral import LocationInfo
import astral.sun
from freezegun import freeze_time
from freezegun.api import FrozenDateTimeFactory
import jinja2
import pytest

from menuai import core as ha
from menuai.const import MATCH_ALL
from menuai.core import (
    Event,
    EventStateChangedData,
    EventStateReportedData,
    menuai,
    callback,
)
from menuai.exceptions import TemplateError
from menuai.helpers.device_registry import EVENT_DEVICE_REGISTRY_UPDATED
from menuai.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED
from menuai.helpers.event import (
    TrackStates,
    TrackTemplate,
    TrackTemplateResult,
    async_call_later,
    async_has_entity_registry_updated_listeners,
    async_track_device_registry_updated_event,
    async_track_entity_registry_updated_event,
    async_track_point_in_time,
    async_track_point_in_utc_time,
    async_track_same_state,
    async_track_state_added_domain,
    async_track_state_change,
    async_track_state_change_event,
    async_track_state_change_filtered,
    async_track_state_removed_domain,
    async_track_state_report_event,
    async_track_sunrise,
    async_track_sunset,
    async_track_template,
    async_track_template_result,
    async_track_time_change,
    async_track_time_interval,
    async_track_utc_time_change,
    track_point_in_utc_time,
)
from menuai.helpers.template import Template, result_as_boolean
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed, async_fire_time_changed_exact

DEFAULT_TIME_ZONE = dt_util.get_default_time_zone()


async def test_track_point_in_time(menuai: menuai) -> None:
    """Test track point in time."""
    before_birthday = datetime(1985, 7, 9, 12, 0, 0, tzinfo=dt_util.UTC)
    birthday_paulus = datetime(1986, 7, 9, 12, 0, 0, tzinfo=dt_util.UTC)
    after_birthday = datetime(1987, 7, 9, 12, 0, 0, tzinfo=dt_util.UTC)

    runs = []

    async_track_point_in_utc_time(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: runs.append(x)),
        birthday_paulus,
    )

    async_fire_time_changed(menuai, before_birthday)
    await menuai.async_block_till_done()
    assert len(runs) == 0

    async_fire_time_changed(menuai, birthday_paulus)
    await menuai.async_block_till_done()
    assert len(runs) == 1

    # A point in time tracker will only fire once, this should do nothing
    async_fire_time_changed(menuai, birthday_paulus)
    await menuai.async_block_till_done()
    assert len(runs) == 1

    async_track_point_in_utc_time(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: runs.append(x)),
        birthday_paulus,
    )

    async_fire_time_changed(menuai, after_birthday)
    await menuai.async_block_till_done()
    assert len(runs) == 2

    unsub = async_track_point_in_time(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: runs.append(x)),
        birthday_paulus,
    )
    unsub()

    async_fire_time_changed(menuai, after_birthday)
    await menuai.async_block_till_done()
    assert len(runs) == 2


async def test_track_point_in_time_drift_rearm(menuai: menuai) -> None:
    """Test tasks with the time rolling backwards."""
    specific_runs = []

    now = dt_util.utcnow()

    time_that_will_not_match_right_away = datetime(
        now.year + 1, 5, 24, 21, 59, 55, tzinfo=dt_util.UTC
    )

    async_track_point_in_utc_time(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: specific_runs.append(x)),
        time_that_will_not_match_right_away,
    )

    async_fire_time_changed(
        menuai,
        datetime(now.year + 1, 5, 24, 21, 59, 00, tzinfo=dt_util.UTC),
        fire_all=True,
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0

    async_fire_time_changed(
        menuai,
        datetime(now.year + 1, 5, 24, 21, 59, 55, tzinfo=dt_util.UTC),
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1


async def test_track_state_change_from_to_state_match(menuai: menuai) -> None:
    """Test track_state_change with from and to state matchers."""
    from_and_to_state_runs = []
    only_from_runs = []
    only_to_runs = []
    match_all_runs = []
    no_to_from_specified_runs = []

    def from_and_to_state_callback(entity_id, old_state, new_state):
        from_and_to_state_runs.append(1)

    def only_from_state_callback(entity_id, old_state, new_state):
        only_from_runs.append(1)

    def only_to_state_callback(entity_id, old_state, new_state):
        only_to_runs.append(1)

    def match_all_callback(entity_id, old_state, new_state):
        match_all_runs.append(1)

    def no_to_from_specified_callback(entity_id, old_state, new_state):
        no_to_from_specified_runs.append(1)

    async_track_state_change(
        menuai, "light.Bowl", from_and_to_state_callback, "on", "off"
    )
    async_track_state_change(menuai, "light.Bowl", only_from_state_callback, "on", None)
    async_track_state_change(
        menuai, "light.Bowl", only_to_state_callback, None, ["off", "standby"]
    )
    async_track_state_change(
        menuai, "light.Bowl", match_all_callback, MATCH_ALL, MATCH_ALL
    )
    async_track_state_change(menuai, "light.Bowl", no_to_from_specified_callback)

    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(from_and_to_state_runs) == 0
    assert len(only_from_runs) == 0
    assert len(only_to_runs) == 0
    assert len(match_all_runs) == 1
    assert len(no_to_from_specified_runs) == 1

    menuai.states.async_set("light.Bowl", "off")
    await menuai.async_block_till_done()
    assert len(from_and_to_state_runs) == 1
    assert len(only_from_runs) == 1
    assert len(only_to_runs) == 1
    assert len(match_all_runs) == 2
    assert len(no_to_from_specified_runs) == 2

    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(from_and_to_state_runs) == 1
    assert len(only_from_runs) == 1
    assert len(only_to_runs) == 1
    assert len(match_all_runs) == 3
    assert len(no_to_from_specified_runs) == 3

    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(from_and_to_state_runs) == 1
    assert len(only_from_runs) == 1
    assert len(only_to_runs) == 1
    assert len(match_all_runs) == 3
    assert len(no_to_from_specified_runs) == 3

    menuai.states.async_set("light.Bowl", "off")
    await menuai.async_block_till_done()
    assert len(from_and_to_state_runs) == 2
    assert len(only_from_runs) == 2
    assert len(only_to_runs) == 2
    assert len(match_all_runs) == 4
    assert len(no_to_from_specified_runs) == 4

    menuai.states.async_set("light.Bowl", "off")
    await menuai.async_block_till_done()
    assert len(from_and_to_state_runs) == 2
    assert len(only_from_runs) == 2
    assert len(only_to_runs) == 2
    assert len(match_all_runs) == 4
    assert len(no_to_from_specified_runs) == 4


async def test_track_state_change(menuai: menuai) -> None:
    """Test track_state_change."""
    # 2 lists to track how often our callbacks get called
    specific_runs = []
    wildcard_runs = []
    wildercard_runs = []

    def specific_run_callback(entity_id, old_state, new_state):
        specific_runs.append(1)

    # This is the rare use case
    async_track_state_change(menuai, "light.Bowl", specific_run_callback, "on", "off")

    @ha.callback
    def wildcard_run_callback(entity_id, old_state, new_state):
        wildcard_runs.append((old_state, new_state))

    # This is the most common use case
    async_track_state_change(menuai, "light.Bowl", wildcard_run_callback)

    async def wildercard_run_callback(entity_id, old_state, new_state):
        wildercard_runs.append((old_state, new_state))

    async_track_state_change(menuai, MATCH_ALL, wildercard_run_callback)

    # Adding state to state machine
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0
    assert len(wildcard_runs) == 1
    assert len(wildercard_runs) == 1
    assert wildcard_runs[-1][0] is None
    assert wildcard_runs[-1][1] is not None

    # Set same state should not trigger a state change/listener
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0
    assert len(wildcard_runs) == 1
    assert len(wildercard_runs) == 1

    # State change off -> on
    menuai.states.async_set("light.Bowl", "off")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1
    assert len(wildcard_runs) == 2
    assert len(wildercard_runs) == 2

    # State change off -> off
    menuai.states.async_set("light.Bowl", "off", {"some_attr": 1})
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1
    assert len(wildcard_runs) == 3
    assert len(wildercard_runs) == 3

    # State change off -> on
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1
    assert len(wildcard_runs) == 4
    assert len(wildercard_runs) == 4

    menuai.states.async_remove("light.bowl")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1
    assert len(wildcard_runs) == 5
    assert len(wildercard_runs) == 5
    assert wildcard_runs[-1][0] is not None
    assert wildcard_runs[-1][1] is None
    assert wildercard_runs[-1][0] is not None
    assert wildercard_runs[-1][1] is None

    # Set state for different entity id
    menuai.states.async_set("switch.kitchen", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1
    assert len(wildcard_runs) == 5
    assert len(wildercard_runs) == 6


async def test_async_track_state_change_filtered(menuai: menuai) -> None:
    """Test async_track_state_change_filtered."""
    single_entity_id_tracker = []
    multiple_entity_id_tracker = []

    @ha.callback
    def single_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        single_entity_id_tracker.append((old_state, new_state))

    @ha.callback
    def multiple_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        multiple_entity_id_tracker.append((old_state, new_state))

    @ha.callback
    def callback_that_throws(event: Event[EventStateChangedData]) -> None:
        raise ValueError

    track_single = async_track_state_change_filtered(
        menuai, TrackStates(False, {"light.bowl"}, None), single_run_callback
    )
    assert track_single.listeners == {
        "all": False,
        "domains": None,
        "entities": {"light.bowl"},
    }

    track_multi = async_track_state_change_filtered(
        menuai, TrackStates(False, {"light.bowl"}, {"switch"}), multiple_run_callback
    )
    assert track_multi.listeners == {
        "all": False,
        "domains": {"switch"},
        "entities": {"light.bowl"},
    }

    track_throws = async_track_state_change_filtered(
        menuai, TrackStates(False, {"light.bowl"}, {"switch"}), callback_that_throws
    )
    assert track_throws.listeners == {
        "all": False,
        "domains": {"switch"},
        "entities": {"light.bowl"},
    }

    # Adding state to state machine
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert single_entity_id_tracker[-1][0] is None
    assert single_entity_id_tracker[-1][1] is not None
    assert len(multiple_entity_id_tracker) == 1
    assert multiple_entity_id_tracker[-1][0] is None
    assert multiple_entity_id_tracker[-1][1] is not None

    # Set same state should not trigger a state change/listener
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert len(multiple_entity_id_tracker) == 1

    # State change off -> on
    menuai.states.async_set("light.Bowl", "off")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 2
    assert len(multiple_entity_id_tracker) == 2

    # State change off -> off
    menuai.states.async_set("light.Bowl", "off", {"some_attr": 1})
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 3
    assert len(multiple_entity_id_tracker) == 3

    # State change off -> on
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 4
    assert len(multiple_entity_id_tracker) == 4

    menuai.states.async_remove("light.bowl")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 5
    assert single_entity_id_tracker[-1][0] is not None
    assert single_entity_id_tracker[-1][1] is None
    assert len(multiple_entity_id_tracker) == 5
    assert multiple_entity_id_tracker[-1][0] is not None
    assert multiple_entity_id_tracker[-1][1] is None

    # Set state for different entity id
    menuai.states.async_set("switch.kitchen", "on")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 5
    assert len(multiple_entity_id_tracker) == 6

    track_single.async_remove()
    # Ensure unsubing the listener works
    menuai.states.async_set("light.Bowl", "off")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 5
    assert len(multiple_entity_id_tracker) == 7

    assert track_multi.listeners == {
        "all": False,
        "domains": {"switch"},
        "entities": {"light.bowl"},
    }
    track_multi.async_update_listeners(TrackStates(False, {"light.bowl"}, None))
    assert track_multi.listeners == {
        "all": False,
        "domains": None,
        "entities": {"light.bowl"},
    }
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(multiple_entity_id_tracker) == 8
    menuai.states.async_set("switch.kitchen", "off")
    await menuai.async_block_till_done()
    assert len(multiple_entity_id_tracker) == 8

    track_multi.async_update_listeners(TrackStates(True, None, None))
    menuai.states.async_set("switch.kitchen", "off")
    await menuai.async_block_till_done()
    assert len(multiple_entity_id_tracker) == 8
    menuai.states.async_set("switch.any", "off")
    await menuai.async_block_till_done()
    assert len(multiple_entity_id_tracker) == 9

    track_multi.async_remove()
    track_throws.async_remove()


async def test_async_track_state_change_event(menuai: menuai) -> None:
    """Test async_track_state_change_event."""
    single_entity_id_tracker = []
    multiple_entity_id_tracker = []

    @ha.callback
    def single_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        single_entity_id_tracker.append((old_state, new_state))

    @ha.callback
    def multiple_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        multiple_entity_id_tracker.append((old_state, new_state))

    @ha.callback
    def callback_that_throws(event: Event[EventStateChangedData]) -> None:
        raise ValueError

    unsub_single = async_track_state_change_event(
        menuai, ["light.Bowl"], single_run_callback, job_type=ha.menuaiJobType.Callback
    )
    unsub_multi = async_track_state_change_event(
        menuai, ["light.Bowl", "switch.kitchen"], multiple_run_callback
    )
    unsub_throws = async_track_state_change_event(
        menuai, ["light.Bowl", "switch.kitchen"], callback_that_throws
    )

    # Adding state to state machine
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert single_entity_id_tracker[-1][0] is None
    assert single_entity_id_tracker[-1][1] is not None
    assert len(multiple_entity_id_tracker) == 1
    assert multiple_entity_id_tracker[-1][0] is None
    assert multiple_entity_id_tracker[-1][1] is not None

    # Set same state should not trigger a state change/listener
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert len(multiple_entity_id_tracker) == 1

    # State change off -> on
    menuai.states.async_set("light.Bowl", "off")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 2
    assert len(multiple_entity_id_tracker) == 2

    # State change off -> off
    menuai.states.async_set("light.Bowl", "off", {"some_attr": 1})
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 3
    assert len(multiple_entity_id_tracker) == 3

    # State change off -> on
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 4
    assert len(multiple_entity_id_tracker) == 4

    menuai.states.async_remove("light.bowl")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 5
    assert single_entity_id_tracker[-1][0] is not None
    assert single_entity_id_tracker[-1][1] is None
    assert len(multiple_entity_id_tracker) == 5
    assert multiple_entity_id_tracker[-1][0] is not None
    assert multiple_entity_id_tracker[-1][1] is None

    # Set state for different entity id
    menuai.states.async_set("switch.kitchen", "on")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 5
    assert len(multiple_entity_id_tracker) == 6

    unsub_single()
    # Ensure unsubing the listener works
    menuai.states.async_set("light.Bowl", "off")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 5
    assert len(multiple_entity_id_tracker) == 7

    unsub_multi()
    unsub_throws()


async def test_async_track_state_change_event_with_empty_list(
    menuai: menuai,
) -> None:
    """Test async_track_state_change_event passing an empty list of entities."""
    unsub_single = async_track_state_change_event(
        menuai, [], ha.callback(lambda event: None)
    )
    unsub_single2 = async_track_state_change_event(
        menuai, [], ha.callback(lambda event: None)
    )

    unsub_single2()
    unsub_single()


async def test_async_track_state_added_domain(menuai: menuai) -> None:
    """Test async_track_state_added_domain."""
    single_entity_id_tracker = []
    multiple_entity_id_tracker = []

    @ha.callback
    def single_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        single_entity_id_tracker.append((old_state, new_state))

    @ha.callback
    def multiple_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        multiple_entity_id_tracker.append((old_state, new_state))

    @ha.callback
    def callback_that_throws(event):
        raise ValueError

    unsub_single = async_track_state_added_domain(
        menuai, "light", single_run_callback, job_type=ha.menuaiJobType.Callback
    )
    unsub_multi = async_track_state_added_domain(
        menuai, ["light", "switch"], multiple_run_callback
    )
    unsub_throws = async_track_state_added_domain(
        menuai, ["light", "switch"], callback_that_throws
    )

    # Adding state to state machine
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert single_entity_id_tracker[-1][0] is None
    assert single_entity_id_tracker[-1][1] is not None
    assert len(multiple_entity_id_tracker) == 1
    assert multiple_entity_id_tracker[-1][0] is None
    assert multiple_entity_id_tracker[-1][1] is not None

    # Set same state should not trigger a state change/listener
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert len(multiple_entity_id_tracker) == 1

    # State change off -> on - nothing added so no trigger
    menuai.states.async_set("light.Bowl", "off")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert len(multiple_entity_id_tracker) == 1

    # State change off -> off - nothing added so no trigger
    menuai.states.async_set("light.Bowl", "off", {"some_attr": 1})
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert len(multiple_entity_id_tracker) == 1

    # Removing state does not trigger
    menuai.states.async_remove("light.bowl")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert len(multiple_entity_id_tracker) == 1

    # Set state for different entity id
    menuai.states.async_set("switch.kitchen", "on")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert len(multiple_entity_id_tracker) == 2

    unsub_single()
    # Ensure unsubing the listener works
    menuai.states.async_set("light.new", "off")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert len(multiple_entity_id_tracker) == 3

    unsub_multi()
    unsub_throws()


async def test_async_track_state_added_domain_with_empty_list(
    menuai: menuai,
) -> None:
    """Test async_track_state_added_domain passing an empty list of domains."""
    unsub_single = async_track_state_added_domain(
        menuai, [], ha.callback(lambda event: None)
    )
    unsub_single2 = async_track_state_added_domain(
        menuai, [], ha.callback(lambda event: None)
    )

    unsub_single2()
    unsub_single()


async def test_async_track_state_removed_domain_with_empty_list(
    menuai: menuai,
) -> None:
    """Test async_track_state_removed_domain passing an empty list of domains."""
    unsub_single = async_track_state_removed_domain(
        menuai, [], ha.callback(lambda event: None)
    )
    unsub_single2 = async_track_state_removed_domain(
        menuai, [], ha.callback(lambda event: None)
    )

    unsub_single2()
    unsub_single()


async def test_async_track_state_removed_domain(menuai: menuai) -> None:
    """Test async_track_state_removed_domain."""
    single_entity_id_tracker = []
    multiple_entity_id_tracker = []

    @ha.callback
    def single_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        single_entity_id_tracker.append((old_state, new_state))

    @ha.callback
    def multiple_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        multiple_entity_id_tracker.append((old_state, new_state))

    @ha.callback
    def callback_that_throws(event):
        raise ValueError

    unsub_single = async_track_state_removed_domain(
        menuai, "light", single_run_callback, job_type=ha.menuaiJobType.Callback
    )
    unsub_multi = async_track_state_removed_domain(
        menuai, ["light", "switch"], multiple_run_callback
    )
    unsub_throws = async_track_state_removed_domain(
        menuai, ["light", "switch"], callback_that_throws
    )

    # Adding state to state machine
    menuai.states.async_set("light.Bowl", "on")
    menuai.states.async_remove("light.Bowl")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert single_entity_id_tracker[-1][1] is None
    assert single_entity_id_tracker[-1][0] is not None
    assert len(multiple_entity_id_tracker) == 1
    assert multiple_entity_id_tracker[-1][1] is None
    assert multiple_entity_id_tracker[-1][0] is not None

    # Added and than removed (light)
    menuai.states.async_set("light.Bowl", "on")
    menuai.states.async_remove("light.Bowl")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 2
    assert len(multiple_entity_id_tracker) == 2

    # Added and than removed (light)
    menuai.states.async_set("light.Bowl", "off")
    menuai.states.async_remove("light.Bowl")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 3
    assert len(multiple_entity_id_tracker) == 3

    # Added and than removed (light)
    menuai.states.async_set("light.Bowl", "off", {"some_attr": 1})
    menuai.states.async_remove("light.Bowl")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 4
    assert len(multiple_entity_id_tracker) == 4

    # Added and than removed (switch)
    menuai.states.async_set("switch.kitchen", "on")
    menuai.states.async_remove("switch.kitchen")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 4
    assert len(multiple_entity_id_tracker) == 5

    unsub_single()
    # Ensure unsubing the listener works
    menuai.states.async_set("light.new", "off")
    menuai.states.async_remove("light.new")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 4
    assert len(multiple_entity_id_tracker) == 6

    unsub_multi()
    unsub_throws()


async def test_async_track_state_removed_domain_match_all(menuai: menuai) -> None:
    """Test async_track_state_removed_domain with a match_all."""
    single_entity_id_tracker = []
    match_all_entity_id_tracker = []

    @ha.callback
    def single_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        single_entity_id_tracker.append((old_state, new_state))

    @ha.callback
    def match_all_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        match_all_entity_id_tracker.append((old_state, new_state))

    unsub_single = async_track_state_removed_domain(menuai, "light", single_run_callback)
    unsub_match_all = async_track_state_removed_domain(
        menuai, MATCH_ALL, match_all_run_callback
    )
    menuai.states.async_set("light.new", "off")
    menuai.states.async_remove("light.new")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert len(match_all_entity_id_tracker) == 1

    menuai.states.async_set("switch.new", "off")
    menuai.states.async_remove("switch.new")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert len(match_all_entity_id_tracker) == 2

    unsub_match_all()
    unsub_single()
    menuai.states.async_set("switch.new", "off")
    menuai.states.async_remove("switch.new")
    await menuai.async_block_till_done()
    assert len(single_entity_id_tracker) == 1
    assert len(match_all_entity_id_tracker) == 2


async def test_track_template(menuai: menuai) -> None:
    """Test tracking template."""
    specific_runs = []
    wildcard_runs = []
    wildercard_runs = []

    template_condition = Template("{{states.switch.test.state == 'on'}}", menuai)
    template_condition_var = Template(
        "{{states.switch.test.state == 'on' and test == 5}}", menuai
    )

    menuai.states.async_set("switch.test", "off")

    def specific_run_callback(entity_id, old_state, new_state):
        specific_runs.append(1)

    async_track_template(menuai, template_condition, specific_run_callback)

    @ha.callback
    def wildcard_run_callback(entity_id, old_state, new_state):
        wildcard_runs.append((old_state, new_state))

    async_track_template(menuai, template_condition, wildcard_run_callback)

    async def wildercard_run_callback(entity_id, old_state, new_state):
        wildercard_runs.append((old_state, new_state))

    async_track_template(
        menuai, template_condition_var, wildercard_run_callback, {"test": 5}
    )

    menuai.states.async_set("switch.test", "on")
    await menuai.async_block_till_done()

    assert len(specific_runs) == 1
    assert len(wildcard_runs) == 1
    assert len(wildercard_runs) == 1

    menuai.states.async_set("switch.test", "on")
    await menuai.async_block_till_done()

    assert len(specific_runs) == 1
    assert len(wildcard_runs) == 1
    assert len(wildercard_runs) == 1

    menuai.states.async_set("switch.test", "off")
    await menuai.async_block_till_done()

    assert len(specific_runs) == 1
    assert len(wildcard_runs) == 1
    assert len(wildercard_runs) == 1

    menuai.states.async_set("switch.test", "off")
    await menuai.async_block_till_done()

    assert len(specific_runs) == 1
    assert len(wildcard_runs) == 1
    assert len(wildercard_runs) == 1

    menuai.states.async_set("switch.test", "on")
    await menuai.async_block_till_done()

    assert len(specific_runs) == 2
    assert len(wildcard_runs) == 2
    assert len(wildercard_runs) == 2

    template_iterate = Template("{{ (states.switch | length) > 0 }}", menuai)
    iterate_calls = []

    @ha.callback
    def iterate_callback(entity_id, old_state, new_state):
        iterate_calls.append((entity_id, old_state, new_state))

    async_track_template(menuai, template_iterate, iterate_callback)
    await menuai.async_block_till_done()

    menuai.states.async_set("switch.new", "on")
    await menuai.async_block_till_done()

    assert len(iterate_calls) == 1
    assert iterate_calls[0][0] == "switch.new"
    assert iterate_calls[0][1] is None
    assert iterate_calls[0][2].state == "on"


async def test_track_template_error(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test tracking template with error."""
    template_error = Template("{{ (states.switch | lunch) > 0 }}", menuai)
    error_calls = []

    @ha.callback
    def error_callback(entity_id, old_state, new_state):
        error_calls.append((entity_id, old_state, new_state))

    async_track_template(menuai, template_error, error_callback)
    await menuai.async_block_till_done()

    menuai.states.async_set("switch.new", "on")
    await menuai.async_block_till_done()

    assert not error_calls
    assert "lunch" in caplog.text
    assert "TemplateAssertionError" in caplog.text

    caplog.clear()

    with patch.object(Template, "async_render") as render:
        render.return_value = "ok"

        menuai.states.async_set("switch.not_exist", "off")
        await menuai.async_block_till_done()

    assert "no filter named 'lunch'" not in caplog.text
    assert "TemplateAssertionError" not in caplog.text


async def test_track_template_error_can_recover(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test tracking template with error."""
    menuai.states.async_set("switch.data_system", "cow", {"opmode": 0})
    template_error = Template(
        "{{ states.sensor.data_system.attributes['opmode'] == '0' }}", menuai
    )
    error_calls = []

    @ha.callback
    def error_callback(entity_id, old_state, new_state):
        error_calls.append((entity_id, old_state, new_state))

    async_track_template(menuai, template_error, error_callback)
    await menuai.async_block_till_done()
    assert not error_calls

    menuai.states.async_remove("switch.data_system")

    assert "UndefinedError" in caplog.text

    menuai.states.async_set("switch.data_system", "cow", {"opmode": 0})

    caplog.clear()

    assert "UndefinedError" not in caplog.text


async def test_track_template_time_change(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test tracking template with time change."""
    template_error = Template("{{ utcnow().minute % 2 == 0 }}", menuai)
    calls = []

    @ha.callback
    def error_callback(entity_id, old_state, new_state):
        calls.append((entity_id, old_state, new_state))

    start_time = dt_util.utcnow() + timedelta(hours=24)
    time_that_will_not_match_right_away = start_time.replace(minute=1, second=0)
    freezer.move_to(time_that_will_not_match_right_away)
    unsub = async_track_template(menuai, template_error, error_callback)
    await menuai.async_block_till_done()
    assert not calls

    first_time = start_time.replace(minute=2, second=0)
    freezer.move_to(first_time)
    async_fire_time_changed(menuai, first_time)
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0] == (None, None, None)

    unsub()


async def test_track_template_result(menuai: menuai) -> None:
    """Test tracking template."""
    specific_runs = []
    wildcard_runs = []
    wildercard_runs = []

    template_condition = Template("{{states.sensor.test.state}}", menuai)
    template_condition_var = Template(
        "{{(states.sensor.test.state|int) + test }}", menuai
    )

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        track_result = updates.pop()
        specific_runs.append(int(track_result.result))

    async_track_template_result(
        menuai, [TrackTemplate(template_condition, None)], specific_run_callback
    )

    @ha.callback
    def wildcard_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        track_result = updates.pop()
        wildcard_runs.append(
            (int(track_result.last_result or 0), int(track_result.result))
        )

    async_track_template_result(
        menuai, [TrackTemplate(template_condition, None)], wildcard_run_callback
    )

    async def wildercard_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        track_result = updates.pop()
        wildercard_runs.append(
            (int(track_result.last_result or 0), int(track_result.result))
        )

    async_track_template_result(
        menuai,
        [TrackTemplate(template_condition_var, {"test": 5})],
        wildercard_run_callback,
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test", 5)
    await menuai.async_block_till_done()

    assert specific_runs == [5]
    assert wildcard_runs == [(0, 5)]
    assert wildercard_runs == [(0, 10)]

    menuai.states.async_set("sensor.test", 30)
    await menuai.async_block_till_done()

    assert specific_runs == [5, 30]
    assert wildcard_runs == [(0, 5), (5, 30)]
    assert wildercard_runs == [(0, 10), (10, 35)]

    menuai.states.async_set("sensor.test", 30)
    await menuai.async_block_till_done()

    assert len(specific_runs) == 2
    assert len(wildcard_runs) == 2
    assert len(wildercard_runs) == 2

    menuai.states.async_set("sensor.test", 5)
    await menuai.async_block_till_done()

    assert len(specific_runs) == 3
    assert len(wildcard_runs) == 3
    assert len(wildercard_runs) == 3

    menuai.states.async_set("sensor.test", 5)
    await menuai.async_block_till_done()

    assert len(specific_runs) == 3
    assert len(wildcard_runs) == 3
    assert len(wildercard_runs) == 3

    menuai.states.async_set("sensor.test", 20)
    await menuai.async_block_till_done()

    assert len(specific_runs) == 4
    assert len(wildcard_runs) == 4
    assert len(wildercard_runs) == 4


async def test_track_template_result_none(menuai: menuai) -> None:
    """Test tracking template."""
    specific_runs = []
    wildcard_runs = []
    wildercard_runs = []

    template_condition = Template("{{state_attr('sensor.test', 'battery')}}", menuai)
    template_condition_var = Template(
        "{{(state_attr('sensor.test', 'battery')|int(default=0)) + test }}", menuai
    )

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        track_result = updates.pop()
        result = int(track_result.result) if track_result.result is not None else None
        specific_runs.append(result)

    async_track_template_result(
        menuai, [TrackTemplate(template_condition, None)], specific_run_callback
    )

    @ha.callback
    def wildcard_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        track_result = updates.pop()
        last_result = (
            int(track_result.last_result)
            if track_result.last_result is not None
            else None
        )
        result = int(track_result.result) if track_result.result is not None else None
        wildcard_runs.append((last_result, result))

    async_track_template_result(
        menuai, [TrackTemplate(template_condition, None)], wildcard_run_callback
    )

    async def wildercard_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        track_result = updates.pop()
        last_result = (
            int(track_result.last_result)
            if track_result.last_result is not None
            else None
        )
        result = int(track_result.result) if track_result.result is not None else None
        wildercard_runs.append((last_result, result))

    async_track_template_result(
        menuai,
        [TrackTemplate(template_condition_var, {"test": 5})],
        wildercard_run_callback,
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test", "-")
    await menuai.async_block_till_done()

    assert specific_runs == [None]
    assert wildcard_runs == [(None, None)]
    assert wildercard_runs == [(None, 5)]

    menuai.states.async_set("sensor.test", "-", {"battery": 5})
    await menuai.async_block_till_done()

    assert specific_runs == [None, 5]
    assert wildcard_runs == [(None, None), (None, 5)]
    assert wildercard_runs == [(None, 5), (5, 10)]


async def test_track_template_result_super_template(menuai: menuai) -> None:
    """Test tracking template with super template listening to same entity."""
    specific_runs = []
    specific_runs_availability = []
    wildcard_runs = []
    wildcard_runs_availability = []
    wildercard_runs = []
    wildercard_runs_availability = []

    template_availability = Template("{{ is_number(states('sensor.test')) }}", menuai)
    template_condition = Template("{{states.sensor.test.state}}", menuai)
    template_condition_var = Template(
        "{{(states.sensor.test.state|int) + test }}", menuai
    )

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_condition:
                specific_runs.append(int(track_result.result))
            elif track_result.template is template_availability:
                specific_runs_availability.append(track_result.result)

    async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_condition, None),
        ],
        specific_run_callback,
        has_super_template=True,
    )

    @ha.callback
    def wildcard_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_condition:
                wildcard_runs.append(
                    (int(track_result.last_result or 0), int(track_result.result))
                )
            elif track_result.template is template_availability:
                wildcard_runs_availability.append(track_result.result)

    async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_condition, None),
        ],
        wildcard_run_callback,
        has_super_template=True,
    )

    async def wildercard_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_condition_var:
                wildercard_runs.append(
                    (int(track_result.last_result or 0), int(track_result.result))
                )
            elif track_result.template is template_availability:
                wildercard_runs_availability.append(track_result.result)

    async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_condition_var, {"test": 5}),
        ],
        wildercard_run_callback,
        has_super_template=True,
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test", "unavailable")
    await menuai.async_block_till_done()

    assert specific_runs_availability == [False]
    assert wildcard_runs_availability == [False]
    assert wildercard_runs_availability == [False]
    assert specific_runs == []
    assert wildcard_runs == []
    assert wildercard_runs == []

    menuai.states.async_set("sensor.test", 5)
    await menuai.async_block_till_done()

    assert specific_runs_availability == [False, True]
    assert wildcard_runs_availability == [False, True]
    assert wildercard_runs_availability == [False, True]
    assert specific_runs == [5]
    assert wildcard_runs == [(0, 5)]
    assert wildercard_runs == [(0, 10)]

    menuai.states.async_set("sensor.test", "unknown")
    await menuai.async_block_till_done()

    assert specific_runs_availability == [False, True, False]
    assert wildcard_runs_availability == [False, True, False]
    assert wildercard_runs_availability == [False, True, False]

    menuai.states.async_set("sensor.test", 30)
    await menuai.async_block_till_done()

    assert specific_runs_availability == [False, True, False, True]
    assert wildcard_runs_availability == [False, True, False, True]
    assert wildercard_runs_availability == [False, True, False, True]

    assert specific_runs == [5, 30]
    assert wildcard_runs == [(0, 5), (5, 30)]
    assert wildercard_runs == [(0, 10), (10, 35)]

    menuai.states.async_set("sensor.test", "other")
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test", 30)
    await menuai.async_block_till_done()

    assert len(specific_runs) == 2
    assert len(wildcard_runs) == 2
    assert len(wildercard_runs) == 2
    assert len(specific_runs_availability) == 6
    assert len(wildcard_runs_availability) == 6
    assert len(wildercard_runs_availability) == 6

    menuai.states.async_set("sensor.test", 30)
    await menuai.async_block_till_done()

    assert len(specific_runs) == 2
    assert len(wildcard_runs) == 2
    assert len(wildercard_runs) == 2
    assert len(specific_runs_availability) == 6
    assert len(wildcard_runs_availability) == 6
    assert len(wildercard_runs_availability) == 6

    menuai.states.async_set("sensor.test", 31)
    await menuai.async_block_till_done()

    assert len(specific_runs) == 3
    assert len(wildcard_runs) == 3
    assert len(wildercard_runs) == 3
    assert len(specific_runs_availability) == 6
    assert len(wildcard_runs_availability) == 6
    assert len(wildercard_runs_availability) == 6


async def test_track_template_result_super_template_initially_false(
    menuai: menuai,
) -> None:
    """Test tracking template with super template listening to same entity."""
    specific_runs = []
    specific_runs_availability = []
    wildcard_runs = []
    wildcard_runs_availability = []
    wildercard_runs = []
    wildercard_runs_availability = []

    template_availability = Template("{{ is_number(states('sensor.test')) }}", menuai)
    template_condition = Template("{{states.sensor.test.state}}", menuai)
    template_condition_var = Template(
        "{{(states.sensor.test.state|int) + test }}", menuai
    )

    # Make the super template initially false
    menuai.states.async_set("sensor.test", "unavailable")
    await menuai.async_block_till_done()

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_condition:
                specific_runs.append(int(track_result.result))
            elif track_result.template is template_availability:
                specific_runs_availability.append(track_result.result)

    async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_condition, None),
        ],
        specific_run_callback,
        has_super_template=True,
    )

    @ha.callback
    def wildcard_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_condition:
                wildcard_runs.append(
                    (int(track_result.last_result or 0), int(track_result.result))
                )
            elif track_result.template is template_availability:
                wildcard_runs_availability.append(track_result.result)

    async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_condition, None),
        ],
        wildcard_run_callback,
        has_super_template=True,
    )

    async def wildercard_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_condition_var:
                wildercard_runs.append(
                    (int(track_result.last_result or 0), int(track_result.result))
                )
            elif track_result.template is template_availability:
                wildercard_runs_availability.append(track_result.result)

    async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_condition_var, {"test": 5}),
        ],
        wildercard_run_callback,
        has_super_template=True,
    )
    await menuai.async_block_till_done()

    assert specific_runs_availability == []
    assert wildcard_runs_availability == []
    assert wildercard_runs_availability == []
    assert specific_runs == []
    assert wildcard_runs == []
    assert wildercard_runs == []

    menuai.states.async_set("sensor.test", 5)
    await menuai.async_block_till_done()

    assert specific_runs_availability == [True]
    assert wildcard_runs_availability == [True]
    assert wildercard_runs_availability == [True]
    assert specific_runs == [5]
    assert wildcard_runs == [(0, 5)]
    assert wildercard_runs == [(0, 10)]

    menuai.states.async_set("sensor.test", "unknown")
    await menuai.async_block_till_done()

    assert specific_runs_availability == [True, False]
    assert wildcard_runs_availability == [True, False]
    assert wildercard_runs_availability == [True, False]

    menuai.states.async_set("sensor.test", 30)
    await menuai.async_block_till_done()

    assert specific_runs_availability == [True, False, True]
    assert wildcard_runs_availability == [True, False, True]
    assert wildercard_runs_availability == [True, False, True]

    assert specific_runs == [5, 30]
    assert wildcard_runs == [(0, 5), (5, 30)]
    assert wildercard_runs == [(0, 10), (10, 35)]

    menuai.states.async_set("sensor.test", "other")
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test", 30)
    await menuai.async_block_till_done()

    assert len(specific_runs) == 2
    assert len(wildcard_runs) == 2
    assert len(wildercard_runs) == 2
    assert len(specific_runs_availability) == 5
    assert len(wildcard_runs_availability) == 5
    assert len(wildercard_runs_availability) == 5

    menuai.states.async_set("sensor.test", 30)
    await menuai.async_block_till_done()

    assert len(specific_runs) == 2
    assert len(wildcard_runs) == 2
    assert len(wildercard_runs) == 2
    assert len(specific_runs_availability) == 5
    assert len(wildcard_runs_availability) == 5
    assert len(wildercard_runs_availability) == 5

    menuai.states.async_set("sensor.test", 31)
    await menuai.async_block_till_done()

    assert len(specific_runs) == 3
    assert len(wildcard_runs) == 3
    assert len(wildercard_runs) == 3
    assert len(specific_runs_availability) == 5
    assert len(wildcard_runs_availability) == 5
    assert len(wildercard_runs_availability) == 5


@pytest.mark.parametrize(
    "availability_template",
    [
        "{{ states('sensor.test2') != 'unavailable' }}",
        "{% if states('sensor.test2') != 'unavailable' -%} true {%- else -%} false {%- endif %}",
        "{% if states('sensor.test2') != 'unavailable' -%} 1 {%- else -%} 0 {%- endif %}",
        "{% if states('sensor.test2') != 'unavailable' -%} yes {%- else -%} no {%- endif %}",
        "{% if states('sensor.test2') != 'unavailable' -%} on {%- else -%} off {%- endif %}",
        "{% if states('sensor.test2') != 'unavailable' -%} enable {%- else -%} disable {%- endif %}",
        # This will throw when sensor.test2 is not "unavailable"
        "{% if states('sensor.test2') != 'unavailable' -%} {{'a' + 5}} {%- else -%} false {%- endif %}",
    ],
)
async def test_track_template_result_super_template_2(
    menuai: menuai, availability_template: str
) -> None:
    """Test tracking template with super template listening to different entities."""
    specific_runs = []
    specific_runs_availability = []
    wildcard_runs = []
    wildcard_runs_availability = []
    wildercard_runs = []
    wildercard_runs_availability = []

    template_availability = Template(availability_template, menuai)
    template_condition = Template("{{states.sensor.test.state}}", menuai)
    template_condition_var = Template(
        "{{(states.sensor.test.state|int) + test }}", menuai
    )

    def _super_template_as_boolean(result):
        if isinstance(result, TemplateError):
            return True

        return result_as_boolean(result)

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_condition:
                specific_runs.append(int(track_result.result))
            elif track_result.template is template_availability:
                specific_runs_availability.append(
                    _super_template_as_boolean(track_result.result)
                )

    info = async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_condition, None),
        ],
        specific_run_callback,
        has_super_template=True,
    )

    @ha.callback
    def wildcard_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_condition:
                wildcard_runs.append(
                    (int(track_result.last_result or 0), int(track_result.result))
                )
            elif track_result.template is template_availability:
                wildcard_runs_availability.append(
                    _super_template_as_boolean(track_result.result)
                )

    info2 = async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_condition, None),
        ],
        wildcard_run_callback,
        has_super_template=True,
    )

    async def wildercard_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_condition_var:
                wildercard_runs.append(
                    (int(track_result.last_result or 0), int(track_result.result))
                )
            elif track_result.template is template_availability:
                wildercard_runs_availability.append(
                    _super_template_as_boolean(track_result.result)
                )

    info3 = async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_condition_var, {"test": 5}),
        ],
        wildercard_run_callback,
        has_super_template=True,
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test2", "unavailable")
    await menuai.async_block_till_done()

    assert specific_runs_availability == [False]
    assert wildcard_runs_availability == [False]
    assert wildercard_runs_availability == [False]
    assert specific_runs == []
    assert wildcard_runs == []
    assert wildercard_runs == []

    menuai.states.async_set("sensor.test", 5)
    menuai.states.async_set("sensor.test2", "available")
    await menuai.async_block_till_done()

    assert specific_runs_availability == [False, True]
    assert wildcard_runs_availability == [False, True]
    assert wildercard_runs_availability == [False, True]
    assert specific_runs == [5]
    assert wildcard_runs == [(0, 5)]
    assert wildercard_runs == [(0, 10)]

    menuai.states.async_set("sensor.test2", "unknown")
    await menuai.async_block_till_done()

    assert specific_runs_availability == [False, True]
    assert wildcard_runs_availability == [False, True]
    assert wildercard_runs_availability == [False, True]

    menuai.states.async_set("sensor.test2", "available")
    menuai.states.async_set("sensor.test", 30)
    await menuai.async_block_till_done()

    assert specific_runs_availability == [False, True]
    assert wildcard_runs_availability == [False, True]
    assert wildercard_runs_availability == [False, True]
    assert specific_runs == [5, 30]
    assert wildcard_runs == [(0, 5), (5, 30)]
    assert wildercard_runs == [(0, 10), (10, 35)]

    info.async_remove()
    info2.async_remove()
    info3.async_remove()


@pytest.mark.parametrize(
    "availability_template",
    [
        "{{ states('sensor.test2') != 'unavailable' }}",
        "{% if states('sensor.test2') != 'unavailable' -%} true {%- else -%} false {%- endif %}",
        "{% if states('sensor.test2') != 'unavailable' -%} 1 {%- else -%} 0 {%- endif %}",
        "{% if states('sensor.test2') != 'unavailable' -%} yes {%- else -%} no {%- endif %}",
        "{% if states('sensor.test2') != 'unavailable' -%} on {%- else -%} off {%- endif %}",
        "{% if states('sensor.test2') != 'unavailable' -%} enable {%- else -%} disable {%- endif %}",
        # This will throw when sensor.test2 is not "unavailable"
        "{% if states('sensor.test2') != 'unavailable' -%} {{'a' + 5}} {%- else -%} false {%- endif %}",
    ],
)
async def test_track_template_result_super_template_2_initially_false(
    menuai: menuai, availability_template: str
) -> None:
    """Test tracking template with super template listening to different entities."""
    specific_runs = []
    specific_runs_availability = []
    wildcard_runs = []
    wildcard_runs_availability = []
    wildercard_runs = []
    wildercard_runs_availability = []

    template_availability = Template(availability_template, menuai)
    template_condition = Template("{{states.sensor.test.state}}", menuai)
    template_condition_var = Template(
        "{{(states.sensor.test.state|int) + test }}", menuai
    )

    menuai.states.async_set("sensor.test2", "unavailable")
    await menuai.async_block_till_done()

    def _super_template_as_boolean(result):
        if isinstance(result, TemplateError):
            return True

        return result_as_boolean(result)

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_condition:
                specific_runs.append(int(track_result.result))
            elif track_result.template is template_availability:
                specific_runs_availability.append(
                    _super_template_as_boolean(track_result.result)
                )

    info = async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_condition, None),
        ],
        specific_run_callback,
        has_super_template=True,
    )

    @ha.callback
    def wildcard_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_condition:
                wildcard_runs.append(
                    (int(track_result.last_result or 0), int(track_result.result))
                )
            elif track_result.template is template_availability:
                wildcard_runs_availability.append(
                    _super_template_as_boolean(track_result.result)
                )

    info2 = async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_condition, None),
        ],
        wildcard_run_callback,
        has_super_template=True,
    )

    async def wildercard_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_condition_var:
                wildercard_runs.append(
                    (int(track_result.last_result or 0), int(track_result.result))
                )
            elif track_result.template is template_availability:
                wildercard_runs_availability.append(
                    _super_template_as_boolean(track_result.result)
                )

    info3 = async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_condition_var, {"test": 5}),
        ],
        wildercard_run_callback,
        has_super_template=True,
    )
    await menuai.async_block_till_done()

    assert specific_runs_availability == []
    assert wildcard_runs_availability == []
    assert wildercard_runs_availability == []
    assert specific_runs == []
    assert wildcard_runs == []
    assert wildercard_runs == []

    menuai.states.async_set("sensor.test", 5)
    menuai.states.async_set("sensor.test2", "available")
    await menuai.async_block_till_done()

    assert specific_runs_availability == [True]
    assert wildcard_runs_availability == [True]
    assert wildercard_runs_availability == [True]
    assert specific_runs == [5]
    assert wildcard_runs == [(0, 5)]
    assert wildercard_runs == [(0, 10)]

    menuai.states.async_set("sensor.test2", "unknown")
    await menuai.async_block_till_done()

    assert specific_runs_availability == [True]
    assert wildcard_runs_availability == [True]
    assert wildercard_runs_availability == [True]

    menuai.states.async_set("sensor.test2", "available")
    menuai.states.async_set("sensor.test", 30)
    await menuai.async_block_till_done()

    assert specific_runs_availability == [True]
    assert wildcard_runs_availability == [True]
    assert wildercard_runs_availability == [True]
    assert specific_runs == [5, 30]
    assert wildcard_runs == [(0, 5), (5, 30)]
    assert wildercard_runs == [(0, 10), (10, 35)]

    info.async_remove()
    info2.async_remove()
    info3.async_remove()


async def test_track_template_result_complex(menuai: menuai) -> None:
    """Test tracking template."""
    specific_runs = []
    template_complex_str = """
{% if states("sensor.domain") == "light" %}
  {{ states.light | map(attribute='entity_id') | list }}
{% elif states("sensor.domain") == "lock" %}
  {{ states.lock | map(attribute='entity_id') | list }}
{% elif states("sensor.domain") == "single_binary_sensor" %}
  {{ states("binary_sensor.single") }}
{% else %}
  {{ states | map(attribute='entity_id') | list }}
{% endif %}

"""
    template_complex = Template(template_complex_str, menuai)

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        specific_runs.append(updates.pop().result)

    menuai.states.async_set("light.one", "on")
    menuai.states.async_set("lock.one", "locked")

    info = async_track_template_result(
        menuai,
        [TrackTemplate(template_complex, None, 0)],
        specific_run_callback,
    )
    await menuai.async_block_till_done()

    assert info.listeners == {
        "all": True,
        "domains": set(),
        "entities": set(),
        "time": False,
    }

    menuai.states.async_set("sensor.domain", "light")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1
    assert specific_runs[0] == ["light.one"]

    assert info.listeners == {
        "all": False,
        "domains": {"light"},
        "entities": {"sensor.domain"},
        "time": False,
    }

    menuai.states.async_set("sensor.domain", "lock")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2
    assert specific_runs[1] == ["lock.one"]
    assert info.listeners == {
        "all": False,
        "domains": {"lock"},
        "entities": {"sensor.domain"},
        "time": False,
    }

    menuai.states.async_set("sensor.domain", "all")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 3
    assert "light.one" in specific_runs[2]
    assert "lock.one" in specific_runs[2]
    assert "sensor.domain" in specific_runs[2]
    assert info.listeners == {
        "all": True,
        "domains": set(),
        "entities": set(),
        "time": False,
    }

    menuai.states.async_set("sensor.domain", "light")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 4
    assert specific_runs[3] == ["light.one"]
    assert info.listeners == {
        "all": False,
        "domains": {"light"},
        "entities": {"sensor.domain"},
        "time": False,
    }

    menuai.states.async_set("light.two", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 5
    assert "light.one" in specific_runs[4]
    assert "light.two" in specific_runs[4]
    assert "sensor.domain" not in specific_runs[4]
    assert info.listeners == {
        "all": False,
        "domains": {"light"},
        "entities": {"sensor.domain"},
        "time": False,
    }

    menuai.states.async_set("light.three", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 6
    assert "light.one" in specific_runs[5]
    assert "light.two" in specific_runs[5]
    assert "light.three" in specific_runs[5]
    assert "sensor.domain" not in specific_runs[5]
    assert info.listeners == {
        "all": False,
        "domains": {"light"},
        "entities": {"sensor.domain"},
        "time": False,
    }

    menuai.states.async_set("sensor.domain", "lock")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 7
    assert specific_runs[6] == ["lock.one"]
    assert info.listeners == {
        "all": False,
        "domains": {"lock"},
        "entities": {"sensor.domain"},
        "time": False,
    }

    menuai.states.async_set("sensor.domain", "single_binary_sensor")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 8
    assert specific_runs[7] == "unknown"
    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"binary_sensor.single", "sensor.domain"},
        "time": False,
    }

    menuai.states.async_set("binary_sensor.single", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 9
    assert specific_runs[8] == "on"
    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"binary_sensor.single", "sensor.domain"},
        "time": False,
    }

    menuai.states.async_set("sensor.domain", "lock")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 10
    assert specific_runs[9] == ["lock.one"]
    assert info.listeners == {
        "all": False,
        "domains": {"lock"},
        "entities": {"sensor.domain"},
        "time": False,
    }


async def test_track_template_result_with_wildcard(menuai: menuai) -> None:
    """Test tracking template with a wildcard."""
    specific_runs = []
    template_complex_str = r"""

{% for state in states %}
  {% if state.entity_id | regex_match('.*\\.office_') %}
    {{ state.entity_id }}={{ state.state }}
  {% endif %}
{% endfor %}

"""
    template_complex = Template(template_complex_str, menuai)

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        specific_runs.append(updates.pop().result)

    menuai.states.async_set("cover.office_drapes", "closed")
    menuai.states.async_set("cover.office_window", "closed")
    menuai.states.async_set("cover.office_skylight", "open")

    info = async_track_template_result(
        menuai, [TrackTemplate(template_complex, None)], specific_run_callback
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("cover.office_window", "open")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1
    assert info.listeners == {
        "all": True,
        "domains": set(),
        "entities": set(),
        "time": False,
    }

    assert "cover.office_drapes=closed" in specific_runs[0]
    assert "cover.office_window=open" in specific_runs[0]
    assert "cover.office_skylight=open" in specific_runs[0]


async def test_track_template_result_with_group(menuai: menuai) -> None:
    """Test tracking template with a group."""
    menuai.states.async_set("sensor.power_1", 0)
    menuai.states.async_set("sensor.power_2", 200.2)
    menuai.states.async_set("sensor.power_3", 400.4)
    menuai.states.async_set("sensor.power_4", 800.8)

    assert await async_setup_component(
        menuai,
        "group",
        {"group": {"power_sensors": "sensor.power_1,sensor.power_2,sensor.power_3"}},
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("group.power_sensors")
    assert menuai.states.get("group.power_sensors").state

    specific_runs = []
    template_complex_str = r"""

{{ states.group.power_sensors.attributes.entity_id | expand | map(attribute='state')|map('float')|sum  }}

"""
    template_complex = Template(template_complex_str, menuai)

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        specific_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai, [TrackTemplate(template_complex, None)], specific_run_callback
    )
    await menuai.async_block_till_done()

    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {
            "group.power_sensors",
            "sensor.power_1",
            "sensor.power_2",
            "sensor.power_3",
        },
        "time": False,
    }

    menuai.states.async_set("sensor.power_1", 100.1)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    assert specific_runs[0] == 100.1 + 200.2 + 400.4

    menuai.states.async_set("sensor.power_3", 0)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    assert specific_runs[1] == 100.1 + 200.2 + 0

    with patch(
        "menuai.config.load_yaml_config_file",
        return_value={
            "group": {
                "power_sensors": "sensor.power_1,sensor.power_2,sensor.power_3,sensor.power_4",
            }
        },
    ):
        await menuai.services.async_call("group", "reload")
        await menuai.async_block_till_done()

    info.async_refresh()
    await menuai.async_block_till_done()
    assert specific_runs[-1] == 100.1 + 200.2 + 0 + 800.8


async def test_track_template_result_and_conditional(menuai: menuai) -> None:
    """Test tracking template with an and conditional."""
    specific_runs = []
    menuai.states.async_set("light.a", "off")
    menuai.states.async_set("light.b", "off")
    template_str = '{% if states.light.a.state == "on" and states.light.b.state == "on" %}on{% else %}off{% endif %}'

    template = Template(template_str, menuai)

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        specific_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai, [TrackTemplate(template, None)], specific_run_callback
    )
    await menuai.async_block_till_done()
    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"light.a"},
        "time": False,
    }

    menuai.states.async_set("light.b", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0

    menuai.states.async_set("light.a", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1
    assert specific_runs[0] == "on"
    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"light.a", "light.b"},
        "time": False,
    }

    menuai.states.async_set("light.b", "off")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2
    assert specific_runs[1] == "off"
    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"light.a", "light.b"},
        "time": False,
    }

    menuai.states.async_set("light.a", "off")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    menuai.states.async_set("light.b", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    menuai.states.async_set("light.a", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 3
    assert specific_runs[2] == "on"


async def test_track_template_result_and_conditional_upper_case(
    menuai: menuai,
) -> None:
    """Test tracking template with an and conditional with an upper case template."""
    specific_runs = []
    menuai.states.async_set("light.a", "off")
    menuai.states.async_set("light.b", "off")
    template_str = '{% if states.light.A.state == "on" and states.light.B.state == "on" %}on{% else %}off{% endif %}'

    template = Template(template_str, menuai)

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        specific_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai, [TrackTemplate(template, None)], specific_run_callback
    )
    await menuai.async_block_till_done()
    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"light.a"},
        "time": False,
    }

    menuai.states.async_set("light.b", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0

    menuai.states.async_set("light.a", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1
    assert specific_runs[0] == "on"
    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"light.a", "light.b"},
        "time": False,
    }

    menuai.states.async_set("light.b", "off")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2
    assert specific_runs[1] == "off"
    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"light.a", "light.b"},
        "time": False,
    }

    menuai.states.async_set("light.a", "off")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    menuai.states.async_set("light.b", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    menuai.states.async_set("light.a", "on")
    await menuai.async_block_till_done()
    assert len(specific_runs) == 3
    assert specific_runs[2] == "on"


async def test_track_template_result_iterator(menuai: menuai) -> None:
    """Test tracking template."""
    iterator_runs = []

    @ha.callback
    def iterator_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        iterator_runs.append(updates.pop().result)

    async_track_template_result(
        menuai,
        [
            TrackTemplate(
                Template(
                    """
            {% for state in states.sensor %}
                {% if state.state == 'on' %}
                    {{ state.entity_id }},
                {% endif %}
            {% endfor %}
            """,
                    menuai,
                ),
                None,
                0,
            )
        ],
        iterator_callback,
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test", 5)
    await menuai.async_block_till_done()

    assert iterator_runs == [""]

    filter_runs = []

    @ha.callback
    def filter_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        filter_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai,
        [
            TrackTemplate(
                Template(
                    """{{ states.sensor|selectattr("state","equalto","on")
                |join(",", attribute="entity_id") }}""",
                    menuai,
                ),
                None,
                0,
            )
        ],
        filter_callback,
    )
    await menuai.async_block_till_done()
    assert info.listeners == {
        "all": False,
        "domains": {"sensor"},
        "entities": set(),
        "time": False,
    }

    menuai.states.async_set("sensor.test", 6)
    await menuai.async_block_till_done()

    assert filter_runs == [""]
    assert iterator_runs == [""]

    menuai.states.async_set("sensor.new", "on")
    await menuai.async_block_till_done()
    assert iterator_runs == ["", "sensor.new,"]
    assert filter_runs == ["", "sensor.new"]


async def test_track_template_result_errors(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test tracking template with errors in the template."""
    template_syntax_error = Template("{{states.switch", menuai)

    template_not_exist = Template("{{states.switch.not_exist.state }}", menuai)

    syntax_error_runs = []
    not_exist_runs = []

    @ha.callback
    def syntax_error_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        track_result = updates.pop()
        syntax_error_runs.append(
            (
                event,
                track_result.template,
                track_result.last_result,
                track_result.result,
            )
        )

    async_track_template_result(
        menuai, [TrackTemplate(template_syntax_error, None)], syntax_error_listener
    )
    await menuai.async_block_till_done()

    assert len(syntax_error_runs) == 0
    assert "TemplateSyntaxError" in caplog.text

    @ha.callback
    def not_exist_runs_error_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        template_track = updates.pop()
        not_exist_runs.append(
            (
                event,
                template_track.template,
                template_track.last_result,
                template_track.result,
            )
        )

    async_track_template_result(
        menuai,
        [TrackTemplate(template_not_exist, None)],
        not_exist_runs_error_listener,
    )
    await menuai.async_block_till_done()

    assert len(syntax_error_runs) == 0
    assert len(not_exist_runs) == 0

    menuai.states.async_set("switch.not_exist", "off")
    await menuai.async_block_till_done()

    assert len(not_exist_runs) == 1
    assert not_exist_runs[0][0].data.get("entity_id") == "switch.not_exist"
    assert not_exist_runs[0][1] == template_not_exist
    assert not_exist_runs[0][2] is None
    assert not_exist_runs[0][3] == "off"

    menuai.states.async_set("switch.not_exist", "on")
    await menuai.async_block_till_done()

    assert len(syntax_error_runs) == 0
    assert len(not_exist_runs) == 2
    assert not_exist_runs[1][0].data.get("entity_id") == "switch.not_exist"
    assert not_exist_runs[1][1] == template_not_exist
    assert not_exist_runs[1][2] == "off"
    assert not_exist_runs[1][3] == "on"

    with patch.object(Template, "async_render") as render:
        render.side_effect = TemplateError(jinja2.TemplateError())

        menuai.states.async_set("switch.not_exist", "off")
        await menuai.async_block_till_done()

        assert len(not_exist_runs) == 3
        assert not_exist_runs[2][0].data.get("entity_id") == "switch.not_exist"
        assert not_exist_runs[2][1] == template_not_exist
        assert not_exist_runs[2][2] == "on"
        assert isinstance(not_exist_runs[2][3], TemplateError)


async def test_track_template_result_transient_errors(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test tracking template with transient errors in the template."""
    menuai.states.async_set("sensor.error", "unknown")
    template_that_raises_sometimes = Template(
        "{{ states('sensor.error') | float }}", menuai
    )

    sometimes_error_runs = []

    @ha.callback
    def sometimes_error_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        track_result = updates.pop()
        sometimes_error_runs.append(
            (
                event,
                track_result.template,
                track_result.last_result,
                track_result.result,
            )
        )

    info = async_track_template_result(
        menuai,
        [TrackTemplate(template_that_raises_sometimes, None)],
        sometimes_error_listener,
    )
    await menuai.async_block_till_done()

    assert sometimes_error_runs == []
    assert "ValueError" in caplog.text
    assert "ValueError" in repr(info)
    caplog.clear()

    menuai.states.async_set("sensor.error", "unavailable")
    await menuai.async_block_till_done()
    assert len(sometimes_error_runs) == 1
    assert isinstance(sometimes_error_runs[0][3], TemplateError)
    sometimes_error_runs.clear()
    assert "ValueError" in repr(info)

    menuai.states.async_set("sensor.error", "4")
    await menuai.async_block_till_done()
    assert len(sometimes_error_runs) == 1
    assert sometimes_error_runs[0][3] == 4.0
    sometimes_error_runs.clear()
    assert "ValueError" not in repr(info)


async def test_static_string(menuai: menuai) -> None:
    """Test a static string."""
    template_refresh = Template("{{ 'static' }}", menuai)

    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        refresh_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai, [TrackTemplate(template_refresh, None)], refresh_listener
    )
    await menuai.async_block_till_done()
    info.async_refresh()
    await menuai.async_block_till_done()

    assert refresh_runs == ["static"]


async def test_track_template_rate_limit(menuai: menuai) -> None:
    """Test template rate limit."""
    template_refresh = Template("{{ states | count }}", menuai)

    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        refresh_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai,
        [TrackTemplate(template_refresh, None, 0.1)],
        refresh_listener,
    )
    await menuai.async_block_till_done()
    info.async_refresh()
    await menuai.async_block_till_done()

    assert refresh_runs == [0]
    menuai.states.async_set("sensor.one", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0]
    info.async_refresh()
    assert refresh_runs == [0, 1]
    menuai.states.async_set("sensor.TWO", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1]
    next_time = dt_util.utcnow() + timedelta(seconds=0.125)
    with patch(
        "menuai.helpers.ratelimit.time.time", return_value=next_time.timestamp()
    ):
        async_fire_time_changed(menuai, next_time)
        await menuai.async_block_till_done()
    assert refresh_runs == [0, 1, 2]
    menuai.states.async_set("sensor.three", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1, 2]
    menuai.states.async_set("sensor.fOuR", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1, 2]
    next_time = dt_util.utcnow() + timedelta(seconds=0.125 * 2)
    with patch(
        "menuai.helpers.ratelimit.time.time", return_value=next_time.timestamp()
    ):
        async_fire_time_changed(menuai, next_time)
        await menuai.async_block_till_done()
    assert refresh_runs == [0, 1, 2, 4]
    menuai.states.async_set("sensor.five", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1, 2, 4]

    info.async_remove()


async def test_track_template_rate_limit_super(menuai: menuai) -> None:
    """Test template rate limit with super template."""
    template_availability = Template(
        "{{ states('sensor.one') != 'unavailable' }}", menuai
    )
    template_refresh = Template("{{ states | count }}", menuai)

    availability_runs = []
    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_refresh:
                refresh_runs.append(track_result.result)
            elif track_result.template is template_availability:
                availability_runs.append(track_result.result)

    info = async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None),
            TrackTemplate(template_refresh, None, 0.1),
        ],
        refresh_listener,
        has_super_template=True,
    )
    await menuai.async_block_till_done()
    info.async_refresh()
    await menuai.async_block_till_done()

    assert refresh_runs == [0]
    menuai.states.async_set("sensor.one", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0]
    info.async_refresh()
    assert refresh_runs == [0, 1]
    menuai.states.async_set("sensor.two", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1]
    menuai.states.async_set("sensor.one", "unavailable")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1]
    next_time = dt_util.utcnow() + timedelta(seconds=0.125)
    with patch(
        "menuai.helpers.ratelimit.time.time", return_value=next_time.timestamp()
    ):
        async_fire_time_changed(menuai, next_time)
        await menuai.async_block_till_done()
    assert refresh_runs == [0, 1]
    menuai.states.async_set("sensor.three", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1]
    menuai.states.async_set("sensor.four", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1]
    # The super template renders as true -> trigger rerendering of all templates
    menuai.states.async_set("sensor.one", "available")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1, 4]
    next_time = dt_util.utcnow() + timedelta(seconds=0.125 * 2)
    with patch(
        "menuai.helpers.ratelimit.time.time", return_value=next_time.timestamp()
    ):
        async_fire_time_changed(menuai, next_time)
        await menuai.async_block_till_done()
    assert refresh_runs == [0, 1, 4]
    menuai.states.async_set("sensor.five", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1, 4]

    info.async_remove()


async def test_track_template_rate_limit_super_2(menuai: menuai) -> None:
    """Test template rate limit with rate limited super template."""
    # Somewhat forced example of a rate limited template
    template_availability = Template("{{ states | count % 2 == 1 }}", menuai)
    template_refresh = Template("{{ states | count }}", menuai)

    availability_runs = []
    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_refresh:
                refresh_runs.append(track_result.result)
            elif track_result.template is template_availability:
                availability_runs.append(track_result.result)

    info = async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None, 0.1),
            TrackTemplate(template_refresh, None, 0.1),
        ],
        refresh_listener,
        has_super_template=True,
    )
    await menuai.async_block_till_done()
    info.async_refresh()
    await menuai.async_block_till_done()

    assert refresh_runs == []
    menuai.states.async_set("sensor.one", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == []
    info.async_refresh()
    assert refresh_runs == [1]
    menuai.states.async_set("sensor.two", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1]
    next_time = dt_util.utcnow() + timedelta(seconds=0.125)
    with patch(
        "menuai.helpers.ratelimit.time.time", return_value=next_time.timestamp()
    ):
        async_fire_time_changed(menuai, next_time)
        await menuai.async_block_till_done()
    assert refresh_runs == [1]
    menuai.states.async_set("sensor.three", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1]
    menuai.states.async_set("sensor.four", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1]
    menuai.states.async_set("sensor.five", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1]
    next_time = dt_util.utcnow() + timedelta(seconds=0.125 * 2)
    with patch(
        "menuai.helpers.ratelimit.time.time", return_value=next_time.timestamp()
    ):
        async_fire_time_changed(menuai, next_time)
        await menuai.async_block_till_done()
    assert refresh_runs == [1, 5]
    menuai.states.async_set("sensor.six", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1, 5]

    info.async_remove()


async def test_track_template_rate_limit_super_3(menuai: menuai) -> None:
    """Test template with rate limited super template."""
    # Somewhat forced example of a rate limited template
    template_availability = Template("{{ states | count % 2 == 1 }}", menuai)
    template_refresh = Template("{{ states | count }}", menuai)

    availability_runs = []
    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for track_result in updates:
            if track_result.template is template_refresh:
                refresh_runs.append(track_result.result)
            elif track_result.template is template_availability:
                availability_runs.append(track_result.result)

    info = async_track_template_result(
        menuai,
        [
            TrackTemplate(template_availability, None, 0.1),
            TrackTemplate(template_refresh, None),
        ],
        refresh_listener,
        has_super_template=True,
    )
    await menuai.async_block_till_done()
    info.async_refresh()
    await menuai.async_block_till_done()

    assert refresh_runs == []
    menuai.states.async_set("sensor.ONE", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == []
    info.async_refresh()
    assert refresh_runs == [1]
    menuai.states.async_set("sensor.two", "any")
    await menuai.async_block_till_done()
    # The super template is rate limited so stuck at `True`
    assert refresh_runs == [1, 2]
    next_time = dt_util.utcnow() + timedelta(seconds=0.125)
    with patch(
        "menuai.helpers.ratelimit.time.time", return_value=next_time.timestamp()
    ):
        async_fire_time_changed(menuai, next_time)
        await menuai.async_block_till_done()
    assert refresh_runs == [1, 2]
    menuai.states.async_set("sensor.three", "any")
    await menuai.async_block_till_done()
    # The super template is rate limited so stuck at `False`
    assert refresh_runs == [1, 2]
    menuai.states.async_set("sensor.four", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1, 2]
    menuai.states.async_set("sensor.FIVE", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1, 2]
    next_time = dt_util.utcnow() + timedelta(seconds=0.125 * 2)
    with patch(
        "menuai.helpers.ratelimit.time.time", return_value=next_time.timestamp()
    ):
        async_fire_time_changed(menuai, next_time)
        await menuai.async_block_till_done()
    assert refresh_runs == [1, 2, 5]
    menuai.states.async_set("sensor.six", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1, 2, 5, 6]
    menuai.states.async_set("sensor.seven", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1, 2, 5, 6, 7]

    info.async_remove()


async def test_track_template_rate_limit_suppress_listener(menuai: menuai) -> None:
    """Test template rate limit will suppress the listener during the rate limit."""
    template_refresh = Template("{{ states | count }}", menuai)

    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        refresh_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai,
        [TrackTemplate(template_refresh, None, 0.1)],
        refresh_listener,
    )
    await menuai.async_block_till_done()
    info.async_refresh()

    assert info.listeners == {
        "all": True,
        "domains": set(),
        "entities": set(),
        "time": False,
    }
    await menuai.async_block_till_done()

    assert refresh_runs == [0]
    menuai.states.async_set("sensor.oNe", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0]
    info.async_refresh()
    assert refresh_runs == [0, 1]
    menuai.states.async_set("sensor.two", "any")
    await menuai.async_block_till_done()
    # Should be suppressed during the rate limit
    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": set(),
        "time": False,
    }
    assert refresh_runs == [0, 1]
    next_time = dt_util.utcnow() + timedelta(seconds=0.125)
    with patch(
        "menuai.helpers.ratelimit.time.time", return_value=next_time.timestamp()
    ):
        async_fire_time_changed(menuai, next_time)
        await menuai.async_block_till_done()
    # Rate limit released and the all listener returns
    assert info.listeners == {
        "all": True,
        "domains": set(),
        "entities": set(),
        "time": False,
    }
    assert refresh_runs == [0, 1, 2]
    menuai.states.async_set("sensor.Three", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1, 2]
    menuai.states.async_set("sensor.four", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1, 2]
    # Rate limit hit and the all listener is shut off
    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": set(),
        "time": False,
    }
    next_time = dt_util.utcnow() + timedelta(seconds=0.125 * 2)
    with patch(
        "menuai.helpers.ratelimit.time.time", return_value=next_time.timestamp()
    ):
        async_fire_time_changed(menuai, next_time)
        await menuai.async_block_till_done()
    # Rate limit released and the all listener returns
    assert info.listeners == {
        "all": True,
        "domains": set(),
        "entities": set(),
        "time": False,
    }
    assert refresh_runs == [0, 1, 2, 4]
    menuai.states.async_set("sensor.Five", "any")
    await menuai.async_block_till_done()
    # Rate limit hit and the all listener is shut off
    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": set(),
        "time": False,
    }
    assert refresh_runs == [0, 1, 2, 4]

    info.async_remove()


async def test_track_template_rate_limit_five(menuai: menuai) -> None:
    """Test template rate limit of 5 seconds."""
    template_refresh = Template("{{ states | count }}", menuai)

    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        refresh_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai,
        [TrackTemplate(template_refresh, None, 5)],
        refresh_listener,
    )
    await menuai.async_block_till_done()
    info.async_refresh()
    await menuai.async_block_till_done()

    assert refresh_runs == [0]
    menuai.states.async_set("sensor.one", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0]
    info.async_refresh()
    assert refresh_runs == [0, 1]
    menuai.states.async_set("sensor.two", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1]
    menuai.states.async_set("sensor.three", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [0, 1]

    info.async_remove()


async def test_track_template_has_default_rate_limit(menuai: menuai) -> None:
    """Test template has a rate limit by default."""
    menuai.states.async_set("sensor.zero", "any")
    template_refresh = Template("{{ states | list | count }}", menuai)

    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        refresh_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai,
        [TrackTemplate(template_refresh, None)],
        refresh_listener,
    )
    await menuai.async_block_till_done()
    info.async_refresh()
    await menuai.async_block_till_done()

    assert refresh_runs == [1]
    menuai.states.async_set("sensor.one", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1]
    info.async_refresh()
    assert refresh_runs == [1, 2]
    menuai.states.async_set("sensor.two", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1, 2]
    menuai.states.async_set("sensor.three", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1, 2]

    info.async_remove()


async def test_track_template_unavailable_states_has_default_rate_limit(
    menuai: menuai,
) -> None:
    """Test template watching for unavailable states has a rate limit by default."""
    menuai.states.async_set("sensor.zero", "unknown")
    template_refresh = Template(
        "{{ states | selectattr('state', 'in', ['unavailable', 'unknown', 'none']) | list | count }}",
        menuai,
    )

    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        refresh_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai,
        [TrackTemplate(template_refresh, None)],
        refresh_listener,
    )
    await menuai.async_block_till_done()
    info.async_refresh()
    await menuai.async_block_till_done()

    assert refresh_runs == [1]
    menuai.states.async_set("sensor.one", "unknown")
    await menuai.async_block_till_done()
    assert refresh_runs == [1]
    info.async_refresh()
    assert refresh_runs == [1, 2]
    menuai.states.async_set("sensor.two", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == [1, 2]
    menuai.states.async_set("sensor.three", "unknown")
    await menuai.async_block_till_done()
    assert refresh_runs == [1, 2]
    info.async_refresh()
    await menuai.async_block_till_done()
    assert refresh_runs == [1, 2, 3]
    info.async_remove()


async def test_specifically_referenced_entity_is_not_rate_limited(
    menuai: menuai,
) -> None:
    """Test template rate limit of 5 seconds."""
    menuai.states.async_set("sensor.one", "none")

    template_refresh = Template('{{ states | count }}_{{ states("sensor.one") }}', menuai)

    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        refresh_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai,
        [TrackTemplate(template_refresh, None, 5)],
        refresh_listener,
    )
    await menuai.async_block_till_done()
    info.async_refresh()
    await menuai.async_block_till_done()

    assert refresh_runs == ["1_none"]
    menuai.states.async_set("sensor.one", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == ["1_none", "1_any"]
    info.async_refresh()
    assert refresh_runs == ["1_none", "1_any"]
    menuai.states.async_set("sensor.two", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == ["1_none", "1_any"]
    menuai.states.async_set("sensor.three", "any")
    await menuai.async_block_till_done()
    assert refresh_runs == ["1_none", "1_any"]
    menuai.states.async_set("sensor.one", "none")
    await menuai.async_block_till_done()
    assert refresh_runs == ["1_none", "1_any", "3_none"]
    info.async_remove()


async def test_track_two_templates_with_different_rate_limits(
    menuai: menuai,
) -> None:
    """Test two templates with different rate limits."""
    template_one = Template("{{ (states | count) + 0 }}", menuai)
    template_five = Template("{{ states | count }}", menuai)

    refresh_runs = {
        template_one: [],
        template_five: [],
    }

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        for update in updates:
            refresh_runs[update.template].append(update.result)

    info = async_track_template_result(
        menuai,
        [
            TrackTemplate(template_one, None, 0.1),
            TrackTemplate(template_five, None, 5),
        ],
        refresh_listener,
    )

    await menuai.async_block_till_done()
    info.async_refresh()
    await menuai.async_block_till_done()

    assert refresh_runs[template_one] == [0]
    assert refresh_runs[template_five] == [0]
    menuai.states.async_set("sensor.one", "any")
    await menuai.async_block_till_done()
    assert refresh_runs[template_one] == [0]
    assert refresh_runs[template_five] == [0]
    info.async_refresh()
    assert refresh_runs[template_one] == [0, 1]
    assert refresh_runs[template_five] == [0, 1]
    menuai.states.async_set("sensor.two", "any")
    await menuai.async_block_till_done()
    assert refresh_runs[template_one] == [0, 1]
    assert refresh_runs[template_five] == [0, 1]
    next_time = dt_util.utcnow() + timedelta(seconds=0.125 * 1)
    with patch(
        "menuai.helpers.ratelimit.time.time", return_value=next_time.timestamp()
    ):
        async_fire_time_changed(menuai, next_time)
        await menuai.async_block_till_done()
    await menuai.async_block_till_done()
    assert refresh_runs[template_one] == [0, 1, 2]
    assert refresh_runs[template_five] == [0, 1]
    menuai.states.async_set("sensor.three", "any")
    await menuai.async_block_till_done()
    assert refresh_runs[template_one] == [0, 1, 2]
    assert refresh_runs[template_five] == [0, 1]
    menuai.states.async_set("sensor.four", "any")
    await menuai.async_block_till_done()
    assert refresh_runs[template_one] == [0, 1, 2]
    assert refresh_runs[template_five] == [0, 1]
    menuai.states.async_set("sensor.five", "any")
    await menuai.async_block_till_done()
    assert refresh_runs[template_one] == [0, 1, 2]
    assert refresh_runs[template_five] == [0, 1]
    info.async_remove()


async def test_string(menuai: menuai) -> None:
    """Test a string."""
    template_refresh = Template("no_template", menuai)

    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        refresh_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai, [TrackTemplate(template_refresh, None)], refresh_listener
    )
    await menuai.async_block_till_done()
    info.async_refresh()
    await menuai.async_block_till_done()

    assert refresh_runs == ["no_template"]


async def test_track_template_result_refresh_cancel(menuai: menuai) -> None:
    """Test cancelling and refreshing result."""
    template_refresh = Template("{{states.switch.test.state == 'on' and now() }}", menuai)

    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        refresh_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai, [TrackTemplate(template_refresh, None)], refresh_listener
    )
    await menuai.async_block_till_done()

    menuai.states.async_set("switch.test", "off")
    await menuai.async_block_till_done()

    assert refresh_runs == [False]

    assert len(refresh_runs) == 1

    info.async_refresh()
    menuai.states.async_set("switch.test", "on")
    await menuai.async_block_till_done()

    assert len(refresh_runs) == 2
    assert refresh_runs[0] != refresh_runs[1]

    info.async_remove()
    menuai.states.async_set("switch.test", "off")
    await menuai.async_block_till_done()

    assert len(refresh_runs) == 2

    template_refresh = Template("{{ value }}", menuai)
    refresh_runs = []

    info = async_track_template_result(
        menuai,
        [TrackTemplate(template_refresh, {"value": "duck"})],
        refresh_listener,
    )
    await menuai.async_block_till_done()
    info.async_refresh()
    await menuai.async_block_till_done()

    assert refresh_runs == ["duck"]

    info.async_refresh()
    await menuai.async_block_till_done()
    assert refresh_runs == ["duck"]


async def test_async_track_template_result_multiple_templates(
    menuai: menuai,
) -> None:
    """Test tracking multiple templates."""

    template_1 = Template("{{ states.switch.test.state == 'on' }}", menuai)
    template_2 = Template("{{ states.switch.test.state == 'on' }}", menuai)
    template_3 = Template("{{ states.switch.test.state == 'off' }}", menuai)
    template_4 = Template(
        "{{ states.binary_sensor | map(attribute='entity_id') | list }}", menuai
    )

    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        refresh_runs.append(updates)

    async_track_template_result(
        menuai,
        [
            TrackTemplate(template_1, None),
            TrackTemplate(template_2, None),
            TrackTemplate(template_3, None),
            TrackTemplate(template_4, None),
        ],
        refresh_listener,
    )

    menuai.states.async_set("switch.test", "on")
    await menuai.async_block_till_done()

    assert refresh_runs == [
        [
            TrackTemplateResult(template_1, None, True),
            TrackTemplateResult(template_2, None, True),
            TrackTemplateResult(template_3, None, False),
        ]
    ]

    refresh_runs = []
    menuai.states.async_set("switch.test", "off")
    await menuai.async_block_till_done()

    assert refresh_runs == [
        [
            TrackTemplateResult(template_1, True, False),
            TrackTemplateResult(template_2, True, False),
            TrackTemplateResult(template_3, False, True),
        ]
    ]

    refresh_runs = []
    menuai.states.async_set("binary_sensor.test", "off")
    await menuai.async_block_till_done()

    assert refresh_runs == [
        [TrackTemplateResult(template_4, None, ["binary_sensor.test"])]
    ]


async def test_async_track_template_result_multiple_templates_mixing_domain(
    menuai: menuai,
) -> None:
    """Test tracking multiple templates when tracking entities and an entire domain."""

    template_1 = Template("{{ states.switch.test.state == 'on' }}", menuai)
    template_2 = Template("{{ states.switch.test.state == 'on' }}", menuai)
    template_3 = Template("{{ states.switch.test.state == 'off' }}", menuai)
    template_4 = Template(
        "{{ states.switch | sort(attribute='entity_id') | map(attribute='entity_id') | list }}",
        menuai,
    )

    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        refresh_runs.append(updates)

    async_track_template_result(
        menuai,
        [
            TrackTemplate(template_1, None),
            TrackTemplate(template_2, None),
            TrackTemplate(template_3, None),
            TrackTemplate(template_4, None, 0),
        ],
        refresh_listener,
    )

    menuai.states.async_set("switch.test", "on")
    await menuai.async_block_till_done()

    assert refresh_runs == [
        [
            TrackTemplateResult(template_1, None, True),
            TrackTemplateResult(template_2, None, True),
            TrackTemplateResult(template_3, None, False),
            TrackTemplateResult(template_4, None, ["switch.test"]),
        ]
    ]

    refresh_runs = []
    menuai.states.async_set("switch.test", "off")
    await menuai.async_block_till_done()

    assert refresh_runs == [
        [
            TrackTemplateResult(template_1, True, False),
            TrackTemplateResult(template_2, True, False),
            TrackTemplateResult(template_3, False, True),
        ]
    ]

    refresh_runs = []
    menuai.states.async_set("binary_sensor.test", "off")
    await menuai.async_block_till_done()

    assert refresh_runs == []

    refresh_runs = []
    menuai.states.async_set("switch.new", "off")
    await menuai.async_block_till_done()

    assert refresh_runs == [
        [
            TrackTemplateResult(
                template_4, ["switch.test"], ["switch.new", "switch.test"]
            )
        ]
    ]


async def test_track_template_with_time(menuai: menuai) -> None:
    """Test tracking template with time."""

    menuai.states.async_set("switch.test", "on")
    specific_runs = []
    template_complex = Template("{{ states.switch.test.state and now() }}", menuai)

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        specific_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai, [TrackTemplate(template_complex, None)], specific_run_callback
    )
    await menuai.async_block_till_done()

    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"switch.test"},
        "time": True,
    }

    await menuai.async_block_till_done()
    now = dt_util.utcnow()
    async_fire_time_changed(menuai, now + timedelta(seconds=61))
    async_fire_time_changed(menuai, now + timedelta(seconds=61 * 2))
    await menuai.async_block_till_done()
    assert specific_runs[-1] != specific_runs[0]
    info.async_remove()


async def test_track_template_with_time_default(menuai: menuai) -> None:
    """Test tracking template with time."""

    specific_runs = []
    template_complex = Template("{{ now() }}", menuai)

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        specific_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai, [TrackTemplate(template_complex, None)], specific_run_callback
    )
    await menuai.async_block_till_done()

    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": set(),
        "time": True,
    }

    await menuai.async_block_till_done()
    now = dt_util.utcnow()
    async_fire_time_changed(menuai, now + timedelta(seconds=2))
    async_fire_time_changed(menuai, now + timedelta(seconds=4))
    await menuai.async_block_till_done()
    assert len(specific_runs) < 2
    async_fire_time_changed(menuai, now + timedelta(minutes=2))
    await menuai.async_block_till_done()
    async_fire_time_changed(menuai, now + timedelta(minutes=4))
    await menuai.async_block_till_done()
    assert len(specific_runs) >= 2
    assert specific_runs[-1] != specific_runs[0]
    info.async_remove()


async def test_track_template_with_time_that_leaves_scope(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test tracking template with time."""
    now = dt_util.utcnow()
    test_time = datetime(now.year + 1, 5, 24, 11, 59, 1, 500000, tzinfo=dt_util.UTC)
    freezer.move_to(test_time)

    menuai.states.async_set("binary_sensor.washing_machine", "on")
    specific_runs = []
    template_complex = Template(
        """
        {% if states.binary_sensor.washing_machine.state == "on" %}
            {{ now() }}
        {% else %}
            {{ states.binary_sensor.washing_machine.last_updated }}
        {% endif %}
    """,
        menuai,
    )

    def specific_run_callback(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        specific_runs.append(updates.pop().result)

    info = async_track_template_result(
        menuai, [TrackTemplate(template_complex, None)], specific_run_callback
    )
    await menuai.async_block_till_done()

    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"binary_sensor.washing_machine"},
        "time": True,
    }

    menuai.states.async_set("binary_sensor.washing_machine", "off")
    await menuai.async_block_till_done()

    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"binary_sensor.washing_machine"},
        "time": False,
    }

    menuai.states.async_set("binary_sensor.washing_machine", "on")
    await menuai.async_block_till_done()

    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"binary_sensor.washing_machine"},
        "time": True,
    }

    # Verify we do not update before the minute rolls over
    callback_count_before_time_change = len(specific_runs)
    async_fire_time_changed(menuai, test_time)
    await menuai.async_block_till_done()
    assert len(specific_runs) == callback_count_before_time_change

    new_time = test_time + timedelta(seconds=58)
    freezer.move_to(new_time)
    async_fire_time_changed(menuai, new_time)
    await menuai.async_block_till_done()
    assert len(specific_runs) == callback_count_before_time_change

    # Verify we do update on the next change of minute
    new_time = test_time + timedelta(seconds=59)
    freezer.move_to(new_time)
    async_fire_time_changed(menuai, new_time)
    await menuai.async_block_till_done()
    assert len(specific_runs) == callback_count_before_time_change + 1

    info.async_remove()


async def test_async_track_template_result_multiple_templates_mixing_listeners(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test tracking multiple templates with mixing listener types."""

    template_1 = Template("{{ states.switch.test.state == 'on' }}", menuai)
    template_2 = Template("{{ now() and True }}", menuai)

    refresh_runs = []

    @ha.callback
    def refresh_listener(
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        refresh_runs.append(updates)

    now = dt_util.utcnow()

    time_that_will_not_match_right_away = datetime(
        now.year + 1, 5, 24, 11, 59, 55, tzinfo=dt_util.UTC
    )
    freezer.move_to(time_that_will_not_match_right_away)

    info = async_track_template_result(
        menuai,
        [
            TrackTemplate(template_1, None),
            TrackTemplate(template_2, None),
        ],
        refresh_listener,
    )

    assert info.listeners == {
        "all": False,
        "domains": set(),
        "entities": {"switch.test"},
        "time": True,
    }
    menuai.states.async_set("switch.test", "on")
    await menuai.async_block_till_done()

    assert refresh_runs == [
        [
            TrackTemplateResult(template_1, None, True),
        ]
    ]

    refresh_runs = []
    menuai.states.async_set("switch.test", "off")
    await menuai.async_block_till_done()

    assert refresh_runs == [
        [
            TrackTemplateResult(template_1, True, False),
        ]
    ]

    refresh_runs = []
    next_time = time_that_will_not_match_right_away + timedelta(hours=25)
    freezer.move_to(next_time)
    async_fire_time_changed(menuai, next_time)
    await menuai.async_block_till_done()

    assert refresh_runs == [
        [
            TrackTemplateResult(template_2, None, True),
        ]
    ]

    info.async_remove()


async def test_track_same_state_simple_no_trigger(menuai: menuai) -> None:
    """Test track_same_change with no trigger."""
    callback_runs = []
    period = timedelta(minutes=1)

    @ha.callback
    def callback_run_callback():
        callback_runs.append(1)

    async_track_same_state(
        menuai,
        period,
        callback_run_callback,
        callback(lambda _, _2, to_s: to_s.state == "on"),
        entity_ids="light.Bowl",
    )

    # Adding state to state machine
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    assert len(callback_runs) == 0

    # Change state on state machine
    menuai.states.async_set("light.Bowl", "off")
    await menuai.async_block_till_done()
    assert len(callback_runs) == 0

    # change time to track and see if they trigger
    future = dt_util.utcnow() + period
    async_fire_time_changed(menuai, future)
    await menuai.async_block_till_done()
    assert len(callback_runs) == 0


async def test_track_same_state_simple_trigger_check_funct(menuai: menuai) -> None:
    """Test track_same_change with trigger and check funct."""
    callback_runs = []
    check_func = []
    period = timedelta(minutes=1)

    @ha.callback
    def callback_run_callback():
        callback_runs.append(1)

    @ha.callback
    def async_check_func(entity, from_s, to_s):
        check_func.append((entity, from_s, to_s))
        return True

    async_track_same_state(
        menuai,
        period,
        callback_run_callback,
        entity_ids="light.Bowl",
        async_check_same_func=async_check_func,
    )

    # Adding state to state machine
    menuai.states.async_set("light.Bowl", "on")
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()
    assert len(callback_runs) == 0
    assert check_func[-1][2].state == "on"
    assert check_func[-1][0] == "light.bowl"

    # change time to track and see if they trigger
    future = dt_util.utcnow() + period
    async_fire_time_changed(menuai, future)
    await menuai.async_block_till_done()
    assert len(callback_runs) == 1


async def test_track_time_interval(menuai: menuai) -> None:
    """Test tracking time interval."""
    specific_runs = []

    utc_now = dt_util.utcnow()
    unsub = async_track_time_interval(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: specific_runs.append(x)),
        timedelta(seconds=10),
    )

    async_fire_time_changed(menuai, utc_now + timedelta(seconds=5))
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0

    async_fire_time_changed(menuai, utc_now + timedelta(seconds=13))
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    async_fire_time_changed(menuai, utc_now + timedelta(minutes=20))
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    unsub()

    async_fire_time_changed(menuai, utc_now + timedelta(seconds=30))
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2


async def test_track_time_interval_name(menuai: menuai) -> None:
    """Test tracking time interval name.

    This test is to ensure that when a name is passed to async_track_time_interval,
    that the name can be found in the TimerHandle when stringified.
    """
    specific_runs = []
    unique_string = "xZ13"
    unsub = async_track_time_interval(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: specific_runs.append(x)),
        timedelta(seconds=10),
        name=unique_string,
    )
    scheduled = menuai.loop._scheduled
    assert any(handle for handle in scheduled if unique_string in str(handle))
    unsub()

    assert all(handle for handle in scheduled if unique_string not in str(handle))
    await menuai.async_block_till_done()


async def test_track_sunrise(menuai: menuai) -> None:
    """Test track the sunrise."""
    latitude = 32.87336
    longitude = 117.22743

    # Setup sun component
    menuai.config.latitude = latitude
    menuai.config.longitude = longitude

    location = LocationInfo(
        latitude=menuai.config.latitude, longitude=menuai.config.longitude
    )

    # Get next sunrise/sunset
    utc_now = datetime(2014, 5, 24, 12, 0, 0, tzinfo=dt_util.UTC)
    utc_today = utc_now.date()

    mod = -1
    while True:
        next_rising = astral.sun.sunrise(
            location.observer, date=utc_today + timedelta(days=mod)
        )
        if next_rising > utc_now:
            break
        mod += 1

    # Track sunrise
    runs = []
    with freeze_time(utc_now):
        unsub = async_track_sunrise(menuai, callback(lambda: runs.append(1)))

    offset_runs = []
    offset = timedelta(minutes=30)
    with freeze_time(utc_now):
        unsub2 = async_track_sunrise(
            menuai, callback(lambda: offset_runs.append(1)), offset
        )

    # run tests
    with freeze_time(next_rising - offset):
        async_fire_time_changed(menuai, next_rising - offset)
        await menuai.async_block_till_done()
        assert len(runs) == 0
        assert len(offset_runs) == 0

    with freeze_time(next_rising):
        async_fire_time_changed(menuai, next_rising)
        await menuai.async_block_till_done()
        assert len(runs) == 1
        assert len(offset_runs) == 0

    with freeze_time(next_rising + offset):
        async_fire_time_changed(menuai, next_rising + offset)
        await menuai.async_block_till_done()
        assert len(runs) == 1
        assert len(offset_runs) == 1

    unsub()
    unsub2()

    with freeze_time(next_rising + offset):
        async_fire_time_changed(menuai, next_rising + offset)
        await menuai.async_block_till_done()
        assert len(runs) == 1
        assert len(offset_runs) == 1


async def test_track_sunrise_update_location(menuai: menuai) -> None:
    """Test track the sunrise."""
    # Setup sun component
    menuai.config.latitude = 32.87336
    menuai.config.longitude = 117.22743

    location = LocationInfo(
        latitude=menuai.config.latitude, longitude=menuai.config.longitude
    )

    # Get next sunrise
    utc_now = datetime(2014, 5, 24, 12, 0, 0, tzinfo=dt_util.UTC)
    utc_today = utc_now.date()

    mod = -1
    while True:
        next_rising = astral.sun.sunrise(
            location.observer, date=utc_today + timedelta(days=mod)
        )
        if next_rising > utc_now:
            break
        mod += 1

    # Track sunrise
    runs = []
    with freeze_time(utc_now):
        unsub = async_track_sunrise(menuai, callback(lambda: runs.append(1)))

    # Mimic sunrise
    with freeze_time(next_rising):
        async_fire_time_changed(menuai, next_rising)
        await menuai.async_block_till_done()
        assert len(runs) == 1

    # Move!
    with freeze_time(utc_now):
        await menuai.config.async_update(latitude=40.755931, longitude=-73.984606)
        await menuai.async_block_till_done()

    # update location for astral
    location = LocationInfo(
        latitude=menuai.config.latitude, longitude=menuai.config.longitude
    )

    # Mimic sunrise
    with freeze_time(next_rising):
        async_fire_time_changed(menuai, next_rising)
        await menuai.async_block_till_done()
        # Did not increase
        assert len(runs) == 1

    # Get next sunrise
    mod = -1
    while True:
        next_rising = astral.sun.sunrise(
            location.observer, date=utc_today + timedelta(days=mod)
        )
        if next_rising > utc_now:
            break
        mod += 1

    with freeze_time(next_rising):
        # Mimic sunrise at new location
        async_fire_time_changed(menuai, next_rising)
        await menuai.async_block_till_done()
        assert len(runs) == 2

    unsub()


async def test_track_sunset(menuai: menuai) -> None:
    """Test track the sunset."""
    latitude = 32.87336
    longitude = 117.22743

    location = LocationInfo(latitude=latitude, longitude=longitude)

    # Setup sun component
    menuai.config.latitude = latitude
    menuai.config.longitude = longitude

    # Get next sunrise/sunset
    utc_now = datetime(2014, 5, 24, 12, 0, 0, tzinfo=dt_util.UTC)
    utc_today = utc_now.date()

    mod = -1
    while True:
        next_setting = astral.sun.sunset(
            location.observer, date=utc_today + timedelta(days=mod)
        )
        if next_setting > utc_now:
            break
        mod += 1

    # Track sunset
    runs = []
    with freeze_time(utc_now):
        unsub = async_track_sunset(menuai, callback(lambda: runs.append(1)))

    offset_runs = []
    offset = timedelta(minutes=30)
    with freeze_time(utc_now):
        unsub2 = async_track_sunset(
            menuai, callback(lambda: offset_runs.append(1)), offset
        )

    # Run tests
    with freeze_time(next_setting - offset):
        async_fire_time_changed(menuai, next_setting - offset)
        await menuai.async_block_till_done()
        assert len(runs) == 0
        assert len(offset_runs) == 0

    with freeze_time(next_setting):
        async_fire_time_changed(menuai, next_setting)
        await menuai.async_block_till_done()
        assert len(runs) == 1
        assert len(offset_runs) == 0

    with freeze_time(next_setting + offset):
        async_fire_time_changed(menuai, next_setting + offset)
        await menuai.async_block_till_done()
        assert len(runs) == 1
        assert len(offset_runs) == 1

    unsub()
    unsub2()

    with freeze_time(next_setting + offset):
        async_fire_time_changed(menuai, next_setting + offset)
        await menuai.async_block_till_done()
        assert len(runs) == 1
        assert len(offset_runs) == 1


async def test_async_track_time_change(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test tracking time change."""
    none_runs = []
    wildcard_runs = []
    specific_runs = []

    now = dt_util.utcnow()

    time_that_will_not_match_right_away = datetime(
        now.year + 1, 5, 24, 11, 59, 55, tzinfo=dt_util.UTC
    )
    freezer.move_to(time_that_will_not_match_right_away)

    unsub = async_track_time_change(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: none_runs.append(x)),
    )
    unsub_utc = async_track_utc_time_change(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: specific_runs.append(x)),
        second=[0, 30],
    )
    unsub_wildcard = async_track_time_change(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: wildcard_runs.append(x)),
        second="*",
        minute="*",
        hour="*",
    )

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 12, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1
    assert len(wildcard_runs) == 1
    assert len(none_runs) == 1

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 12, 0, 15, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1
    assert len(wildcard_runs) == 2
    assert len(none_runs) == 2

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 12, 0, 30, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2
    assert len(wildcard_runs) == 3
    assert len(none_runs) == 3

    unsub()
    unsub_utc()
    unsub_wildcard()

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 12, 0, 30, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2
    assert len(wildcard_runs) == 3
    assert len(none_runs) == 3


async def test_periodic_task_minute(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test periodic tasks per minute."""
    specific_runs = []

    now = dt_util.utcnow()

    time_that_will_not_match_right_away = datetime(
        now.year + 1, 5, 24, 11, 59, 55, tzinfo=dt_util.UTC
    )
    freezer.move_to(time_that_will_not_match_right_away)

    unsub = async_track_utc_time_change(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: specific_runs.append(x)),
        minute="/5",
        second=0,
    )

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 12, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 12, 3, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 12, 5, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    unsub()

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 12, 5, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2


async def test_periodic_task_hour(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test periodic tasks per hour."""
    specific_runs = []

    now = dt_util.utcnow()

    time_that_will_not_match_right_away = datetime(
        now.year + 1, 5, 24, 21, 59, 55, tzinfo=dt_util.UTC
    )
    freezer.move_to(time_that_will_not_match_right_away)

    unsub = async_track_utc_time_change(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: specific_runs.append(x)),
        hour="/2",
        minute=0,
        second=0,
    )

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 22, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 23, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 25, 0, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 25, 1, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 25, 2, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 3

    unsub()

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 25, 2, 0, 0, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 3


async def test_periodic_task_wrong_input(menuai: menuai) -> None:
    """Test periodic tasks with wrong input."""
    specific_runs = []

    now = dt_util.utcnow()

    with pytest.raises(ValueError):
        async_track_utc_time_change(
            menuai,
            # pylint: disable-next=unnecessary-lambda
            callback(lambda x: specific_runs.append(x)),
            hour="/two",
        )

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 2, 0, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0


async def test_periodic_task_clock_rollback(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test periodic tasks with the time rolling backwards."""
    specific_runs = []

    now = dt_util.utcnow()
    time_that_will_not_match_right_away = datetime(
        now.year + 1, 5, 24, 21, 59, 55, tzinfo=dt_util.UTC
    )
    freezer.move_to(time_that_will_not_match_right_away)

    unsub = async_track_utc_time_change(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: specific_runs.append(x)),
        hour="/2",
        minute=0,
        second=0,
    )

    new_time = datetime(now.year + 1, 5, 24, 22, 0, 0, 999999, tzinfo=dt_util.UTC)
    freezer.move_to(new_time)
    async_fire_time_changed(menuai, new_time)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    new_time = datetime(now.year + 1, 5, 24, 23, 0, 0, 999999, tzinfo=dt_util.UTC)
    freezer.move_to(new_time)
    async_fire_time_changed(menuai, new_time)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    new_time = datetime(now.year + 1, 5, 24, 22, 0, 0, 999999, tzinfo=dt_util.UTC)
    freezer.move_to(new_time)
    async_fire_time_changed(
        menuai,
        new_time,
        fire_all=True,
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    new_time = datetime(now.year + 1, 5, 24, 0, 0, 0, 999999, tzinfo=dt_util.UTC)
    freezer.move_to(new_time)
    async_fire_time_changed(
        menuai,
        new_time,
        fire_all=True,
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    new_time = datetime(now.year + 1, 5, 25, 2, 0, 0, 999999, tzinfo=dt_util.UTC)
    freezer.move_to(new_time)
    async_fire_time_changed(menuai, new_time)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    unsub()

    new_time = datetime(now.year + 1, 5, 25, 2, 0, 0, 999999, tzinfo=dt_util.UTC)
    freezer.move_to(new_time)
    async_fire_time_changed(menuai, new_time)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2


async def test_periodic_task_duplicate_time(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test periodic tasks not triggering on duplicate time."""
    specific_runs = []

    now = dt_util.utcnow()

    time_that_will_not_match_right_away = datetime(
        now.year + 1, 5, 24, 21, 59, 55, tzinfo=dt_util.UTC
    )
    freezer.move_to(time_that_will_not_match_right_away)

    unsub = async_track_utc_time_change(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: specific_runs.append(x)),
        hour="/2",
        minute=0,
        second=0,
    )

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 22, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 22, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 25, 0, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    unsub()


# DST starts early morning March 28th 2021
@pytest.mark.freeze_time("2021-03-28 01:28:00+01:00")
async def test_periodic_task_entering_dst(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test periodic task behavior when entering dst."""
    await menuai.config.async_set_time_zone("Europe/Vienna")
    specific_runs = []

    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # Make sure we enter DST during the test
    now_local = dt_util.now()
    assert now_local.utcoffset() != (now_local + timedelta(hours=2)).utcoffset()

    unsub = async_track_time_change(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: specific_runs.append(x)),
        hour=2,
        minute=30,
        second=0,
    )

    freezer.move_to(f"{today} 01:50:00.999999+01:00")
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0

    # There was no 02:30 today, the event should not fire until tomorrow
    freezer.move_to(f"{today} 03:50:00.999999+02:00")
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0

    freezer.move_to(f"{tomorrow} 01:50:00.999999+02:00")
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0

    freezer.move_to(f"{tomorrow} 02:50:00.999999+02:00")
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    unsub()


# DST starts early morning March 28th 2021
@pytest.mark.freeze_time("2021-03-28 01:59:59+01:00")
async def test_periodic_task_entering_dst_2(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test periodic task behavior when entering dst.

    This tests a task firing every second in the range 0..58 (not *:*:59)
    """
    await menuai.config.async_set_time_zone("Europe/Vienna")
    specific_runs = []

    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # Make sure we enter DST during the test
    now_local = dt_util.now()
    assert now_local.utcoffset() != (now_local + timedelta(hours=2)).utcoffset()

    unsub = async_track_time_change(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: specific_runs.append(x)),
        second=list(range(59)),
    )

    freezer.move_to(f"{today} 01:59:59.999999+01:00")
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0

    freezer.move_to(f"{today} 03:00:00.999999+02:00")
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    freezer.move_to(f"{today} 03:00:01.999999+02:00")
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    freezer.move_to(f"{tomorrow} 01:59:59.999999+02:00")
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 3

    freezer.move_to(f"{tomorrow} 02:00:00.999999+02:00")
    async_fire_time_changed_exact(menuai)
    await menuai.async_block_till_done()
    assert len(specific_runs) == 4

    unsub()


# DST ends early morning October 31st 2021
@pytest.mark.freeze_time("2021-10-31 02:28:00+02:00")
async def test_periodic_task_leaving_dst(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test periodic task behavior when leaving dst."""
    await menuai.config.async_set_time_zone("Europe/Vienna")
    specific_runs = []

    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    # Make sure we leave DST during the test
    now_local = dt_util.now()
    assert now_local.utcoffset() != (now_local + timedelta(hours=1)).utcoffset()

    unsub = async_track_time_change(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: specific_runs.append(x)),
        hour=2,
        minute=30,
        second=0,
    )

    # The task should not fire yet
    freezer.move_to(f"{today} 02:28:00.999999+02:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 0
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0

    # The task should fire
    freezer.move_to(f"{today} 02:30:00.999999+02:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 0
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    # The task should not fire again
    freezer.move_to(f"{today} 02:55:00.999999+02:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 0
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    # DST has ended, the task should not fire yet
    freezer.move_to(f"{today} 02:15:00.999999+01:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 1  # DST has ended
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    # The task should fire
    freezer.move_to(f"{today} 02:45:00.999999+01:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 1
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    # The task should not fire again
    freezer.move_to(f"{today} 02:55:00.999999+01:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 1
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    # The task should fire again the next day
    freezer.move_to(f"{tomorrow} 02:55:00.999999+01:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 0
    await menuai.async_block_till_done()
    assert len(specific_runs) == 3

    unsub()


# DST ends early morning October 31st 2021
@pytest.mark.freeze_time("2021-10-31 02:28:00+02:00")
async def test_periodic_task_leaving_dst_2(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test periodic task behavior when leaving dst."""
    await menuai.config.async_set_time_zone("Europe/Vienna")
    specific_runs = []

    today = date.today().isoformat()

    # Make sure we leave DST during the test
    now_local = dt_util.now()
    assert now_local.utcoffset() != (now_local + timedelta(hours=1)).utcoffset()

    unsub = async_track_time_change(
        menuai,
        # pylint: disable-next=unnecessary-lambda
        callback(lambda x: specific_runs.append(x)),
        minute=30,
        second=0,
    )

    # The task should not fire yet
    freezer.move_to(f"{today} 02:28:00.999999+02:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 0
    await menuai.async_block_till_done()
    assert len(specific_runs) == 0

    # The task should fire
    freezer.move_to(f"{today} 02:55:00.999999+02:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 0
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    # DST has ended, the task should not fire yet
    freezer.move_to(f"{today} 02:15:00.999999+01:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 1
    await menuai.async_block_till_done()
    assert len(specific_runs) == 1

    # The task should fire
    freezer.move_to(f"{today} 02:45:00.999999+01:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 1
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    # The task should not fire again
    freezer.move_to(f"{today} 02:55:00.999999+01:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 1
    await menuai.async_block_till_done()
    assert len(specific_runs) == 2

    # The task should fire again the next hour
    freezer.move_to(f"{today} 03:55:00.999999+01:00")
    async_fire_time_changed(menuai)
    assert dt_util.now().fold == 0
    await menuai.async_block_till_done()
    assert len(specific_runs) == 3

    unsub()


async def test_call_later(menuai: menuai) -> None:
    """Test calling an action later."""
    future = asyncio.get_running_loop().create_future()
    delay = 5
    delay_tolerance = 0.1
    schedule_utctime = dt_util.utcnow()

    @callback
    def action(utcnow: datetime, /):
        _current_delay = utcnow.timestamp() - schedule_utctime.timestamp()
        future.set_result(delay < _current_delay < (delay + delay_tolerance))

    async_call_later(menuai, delay, action)

    async_fire_time_changed_exact(menuai, dt_util.utcnow() + timedelta(seconds=delay))

    async with asyncio.timeout(delay + delay_tolerance):
        assert await future, "callback was called but the delay was wrong"


async def test_async_call_later(menuai: menuai) -> None:
    """Test calling an action later."""
    future = asyncio.get_running_loop().create_future()
    delay = 5
    delay_tolerance = 0.1
    schedule_utctime = dt_util.utcnow()

    @callback
    def action(utcnow: datetime, /):
        _current_delay = utcnow.timestamp() - schedule_utctime.timestamp()
        future.set_result(delay < _current_delay < (delay + delay_tolerance))

    remove = async_call_later(menuai, delay, action)

    async_fire_time_changed_exact(menuai, dt_util.utcnow() + timedelta(seconds=delay))

    async with asyncio.timeout(delay + delay_tolerance):
        assert await future, "callback was called but the delay was wrong"
    assert isinstance(remove, Callable)
    remove()


async def test_async_call_later_timedelta(menuai: menuai) -> None:
    """Test calling an action later with a timedelta."""
    future = asyncio.get_running_loop().create_future()
    delay = 5
    delay_tolerance = 0.1
    schedule_utctime = dt_util.utcnow()

    @callback
    def action(utcnow: datetime, /):
        _current_delay = utcnow.timestamp() - schedule_utctime.timestamp()
        future.set_result(delay < _current_delay < (delay + delay_tolerance))

    remove = async_call_later(menuai, timedelta(seconds=delay), action)

    async_fire_time_changed_exact(menuai, dt_util.utcnow() + timedelta(seconds=delay))

    async with asyncio.timeout(delay + delay_tolerance):
        assert await future, "callback was called but the delay was wrong"
    assert isinstance(remove, Callable)
    remove()


async def test_async_call_later_cancel(menuai: menuai) -> None:
    """Test canceling a call_later action."""
    future = asyncio.get_running_loop().create_future()
    delay = 0.25
    delay_tolerance = 0.1

    @callback
    def action(now: datetime, /):
        future.set_result(False)

    remove = async_call_later(menuai, delay, action)
    # fast forward time a bit..
    async_fire_time_changed_exact(
        menuai, dt_util.utcnow() + timedelta(seconds=delay - delay_tolerance)
    )
    # and remove before firing
    remove()
    # fast forward time beyond scheduled
    async_fire_time_changed_exact(menuai, dt_util.utcnow() + timedelta(seconds=delay))

    with contextlib.suppress(TimeoutError):
        async with asyncio.timeout(delay + delay_tolerance):
            assert await future, "callback not canceled"


async def test_track_state_change_event_chain_multple_entity(
    menuai: menuai,
) -> None:
    """Test that adding a new state tracker inside a tracker does not fire right away."""
    tracker_called = []
    chained_tracker_called = []

    chained_tracker_unsub = []
    tracker_unsub = []

    @ha.callback
    def chained_single_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        chained_tracker_called.append((old_state, new_state))

    @ha.callback
    def single_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        tracker_called.append((old_state, new_state))

        chained_tracker_unsub.append(
            async_track_state_change_event(
                menuai, ["light.bowl", "light.top"], chained_single_run_callback
            )
        )

    tracker_unsub.append(
        async_track_state_change_event(
            menuai, ["light.bowl", "light.top"], single_run_callback
        )
    )

    menuai.states.async_set("light.bowl", "on")
    menuai.states.async_set("light.top", "on")
    await menuai.async_block_till_done()

    assert len(tracker_called) == 2
    assert len(chained_tracker_called) == 1
    assert len(tracker_unsub) == 1
    assert len(chained_tracker_unsub) == 2

    menuai.states.async_set("light.bowl", "off")
    await menuai.async_block_till_done()

    assert len(tracker_called) == 3
    assert len(chained_tracker_called) == 3
    assert len(tracker_unsub) == 1
    assert len(chained_tracker_unsub) == 3


async def test_track_state_change_event_chain_single_entity(
    menuai: menuai,
) -> None:
    """Test that adding a new state tracker inside a tracker does not fire right away."""
    tracker_called = []
    chained_tracker_called = []

    chained_tracker_unsub = []
    tracker_unsub = []

    @ha.callback
    def chained_single_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        chained_tracker_called.append((old_state, new_state))

    @ha.callback
    def single_run_callback(event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        tracker_called.append((old_state, new_state))

        chained_tracker_unsub.append(
            async_track_state_change_event(
                menuai, "light.bowl", chained_single_run_callback
            )
        )

    tracker_unsub.append(
        async_track_state_change_event(menuai, "light.bowl", single_run_callback)
    )

    menuai.states.async_set("light.bowl", "on")
    await menuai.async_block_till_done()

    assert len(tracker_called) == 1
    assert len(chained_tracker_called) == 0
    assert len(tracker_unsub) == 1
    assert len(chained_tracker_unsub) == 1

    menuai.states.async_set("light.bowl", "off")
    await menuai.async_block_till_done()

    assert len(tracker_called) == 2
    assert len(chained_tracker_called) == 1
    assert len(tracker_unsub) == 1
    assert len(chained_tracker_unsub) == 2


async def test_track_point_in_utc_time_cancel(menuai: menuai) -> None:
    """Test cancel of async track point in time."""

    times = []

    @ha.callback
    def run_callback(utc_time):
        nonlocal times
        times.append(utc_time)

    def _setup_listeners():
        """Ensure we test the non-async version."""
        utc_now = dt_util.utcnow()

        with pytest.raises(TypeError):
            track_point_in_utc_time("notmenuai", run_callback, utc_now)

        unsub1 = track_point_in_utc_time(
            menuai, run_callback, utc_now + timedelta(seconds=0.1)
        )
        track_point_in_utc_time(menuai, run_callback, utc_now + timedelta(seconds=0.1))

        unsub1()

    await menuai.async_add_executor_job(_setup_listeners)

    await asyncio.sleep(0.2)

    assert len(times) == 1
    assert times[0].tzinfo == dt_util.UTC


async def test_async_track_point_in_time_cancel(menuai: menuai) -> None:
    """Test cancel of async track point in time."""

    times = []
    await menuai.config.async_set_time_zone("US/Hawaii")
    hst_tz = dt_util.get_time_zone("US/Hawaii")

    @ha.callback
    def run_callback(local_time):
        nonlocal times
        times.append(local_time)

    utc_now = dt_util.utcnow()
    hst_now = utc_now.astimezone(hst_tz)

    unsub1 = async_track_point_in_time(
        menuai, run_callback, hst_now + timedelta(seconds=0.1)
    )
    async_track_point_in_time(menuai, run_callback, hst_now + timedelta(seconds=0.1))

    unsub1()

    await asyncio.sleep(0.2)

    assert len(times) == 1
    assert "US/Hawaii" in str(times[0].tzinfo)


async def test_async_track_point_in_time_cancel_in_job(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test cancel of async track point in time during job execution."""

    now = dt_util.utcnow()
    times = []

    time_that_will_not_match_right_away = datetime(
        now.year + 1, 5, 24, 11, 59, 55, tzinfo=dt_util.UTC
    )
    freezer.move_to(time_that_will_not_match_right_away)

    @callback
    def action(x: datetime):
        nonlocal times
        times.append(x)
        unsub()

    unsub = async_track_utc_time_change(menuai, action, minute=0, second="*")

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 12, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(times) == 1

    async_fire_time_changed(
        menuai, datetime(now.year + 1, 5, 24, 13, 0, 0, 999999, tzinfo=dt_util.UTC)
    )
    await menuai.async_block_till_done()
    assert len(times) == 1


async def test_async_track_entity_registry_updated_event(menuai: menuai) -> None:
    """Test tracking entity registry updates for an entity_id."""

    entity_id = "switch.puppy_feeder"
    new_entity_id = "switch.dog_feeder"
    untracked_entity_id = "switch.kitty_feeder"

    menuai.states.async_set(entity_id, "on")
    await menuai.async_block_till_done()
    event_data = []

    @ha.callback
    def run_callback(event):
        event_data.append(event.data)

    assert async_has_entity_registry_updated_listeners(menuai) is False

    unsub1 = async_track_entity_registry_updated_event(
        menuai, entity_id, run_callback, job_type=ha.menuaiJobType.Callback
    )
    unsub2 = async_track_entity_registry_updated_event(
        menuai, new_entity_id, run_callback
    )

    assert async_has_entity_registry_updated_listeners(menuai) is True

    menuai.bus.async_fire(
        EVENT_ENTITY_REGISTRY_UPDATED, {"action": "create", "entity_id": entity_id}
    )
    menuai.bus.async_fire(
        EVENT_ENTITY_REGISTRY_UPDATED,
        {"action": "create", "entity_id": untracked_entity_id},
    )
    await menuai.async_block_till_done()

    menuai.bus.async_fire(
        EVENT_ENTITY_REGISTRY_UPDATED,
        {
            "action": "update",
            "entity_id": new_entity_id,
            "old_entity_id": entity_id,
            "changes": {},
        },
    )
    await menuai.async_block_till_done()

    menuai.bus.async_fire(
        EVENT_ENTITY_REGISTRY_UPDATED, {"action": "remove", "entity_id": new_entity_id}
    )
    await menuai.async_block_till_done()

    unsub1()
    unsub2()
    menuai.bus.async_fire(
        EVENT_ENTITY_REGISTRY_UPDATED, {"action": "create", "entity_id": entity_id}
    )
    menuai.bus.async_fire(
        EVENT_ENTITY_REGISTRY_UPDATED, {"action": "create", "entity_id": new_entity_id}
    )
    await menuai.async_block_till_done()

    assert event_data[0] == {"action": "create", "entity_id": "switch.puppy_feeder"}
    assert event_data[1] == {
        "action": "update",
        "changes": {},
        "entity_id": "switch.dog_feeder",
        "old_entity_id": "switch.puppy_feeder",
    }
    assert event_data[2] == {"action": "remove", "entity_id": "switch.dog_feeder"}


async def test_async_track_entity_registry_updated_event_with_a_callback_that_throws(
    menuai: menuai,
) -> None:
    """Test tracking entity registry updates for an entity_id when one callback throws."""

    entity_id = "switch.puppy_feeder"

    menuai.states.async_set(entity_id, "on")
    await menuai.async_block_till_done()
    event_data = []

    @ha.callback
    def run_callback(event):
        event_data.append(event.data)

    @ha.callback
    def failing_callback(event):
        raise ValueError

    unsub1 = async_track_entity_registry_updated_event(
        menuai, entity_id, failing_callback
    )
    unsub2 = async_track_entity_registry_updated_event(menuai, entity_id, run_callback)
    menuai.bus.async_fire(
        EVENT_ENTITY_REGISTRY_UPDATED, {"action": "create", "entity_id": entity_id}
    )
    await menuai.async_block_till_done()
    unsub1()
    unsub2()

    assert event_data[0] == {"action": "create", "entity_id": "switch.puppy_feeder"}


async def test_async_track_entity_registry_updated_event_with_empty_list(
    menuai: menuai,
) -> None:
    """Test async_track_entity_registry_updated_event passing an empty list of entities."""
    unsub_single = async_track_entity_registry_updated_event(
        menuai, [], ha.callback(lambda event: None)
    )
    unsub_single2 = async_track_entity_registry_updated_event(
        menuai, [], ha.callback(lambda event: None)
    )

    unsub_single2()
    unsub_single()


async def test_async_track_device_registry_updated_event(menuai: menuai) -> None:
    """Test tracking device registry updates for an device_id."""

    device_id = "b92c0f06fbc911edacc9eea8ae14f866"
    device_id2 = "747bbf22fbca11ed843aeea8ae14f866"
    untracked_device_id = "bda93f86fbc911edacc9eea8ae14f866"

    single_event_data = []
    multiple_event_data = []

    @ha.callback
    def single_device_id_callback(event: ha.Event) -> None:
        single_event_data.append(event.data)

    @ha.callback
    def multiple_device_id_callback(event: ha.Event) -> None:
        multiple_event_data.append(event.data)

    unsub1 = async_track_device_registry_updated_event(
        menuai, device_id, single_device_id_callback
    )
    unsub2 = async_track_device_registry_updated_event(
        menuai,
        [device_id, device_id2],
        multiple_device_id_callback,
        job_type=ha.menuaiJobType.Callback,
    )
    menuai.bus.async_fire(
        EVENT_DEVICE_REGISTRY_UPDATED, {"action": "create", "device_id": device_id}
    )
    menuai.bus.async_fire(
        EVENT_ENTITY_REGISTRY_UPDATED,
        {"action": "create", "device_id": untracked_device_id},
    )
    await menuai.async_block_till_done()
    assert len(single_event_data) == 1
    assert len(multiple_event_data) == 1
    menuai.bus.async_fire(
        EVENT_DEVICE_REGISTRY_UPDATED, {"action": "create", "device_id": device_id2}
    )
    await menuai.async_block_till_done()
    assert len(single_event_data) == 1
    assert len(multiple_event_data) == 2

    unsub1()
    unsub2()
    menuai.bus.async_fire(
        EVENT_ENTITY_REGISTRY_UPDATED, {"action": "create", "device_id": device_id}
    )
    menuai.bus.async_fire(
        EVENT_ENTITY_REGISTRY_UPDATED, {"action": "create", "device_id": device_id2}
    )
    await menuai.async_block_till_done()
    assert len(single_event_data) == 1
    assert len(multiple_event_data) == 2


async def test_async_track_device_registry_updated_event_with_empty_list(
    menuai: menuai,
) -> None:
    """Test async_track_device_registry_updated_event passing an empty list of devices."""
    unsub_single = async_track_device_registry_updated_event(
        menuai, [], ha.callback(lambda event: None)
    )
    unsub_single2 = async_track_device_registry_updated_event(
        menuai, [], ha.callback(lambda event: None)
    )

    unsub_single2()
    unsub_single()


async def test_async_track_device_registry_updated_event_with_a_callback_that_throws(
    menuai: menuai,
) -> None:
    """Test tracking device registry updates for an device when one callback throws."""

    device_id = "b92c0f06fbc911edacc9eea8ae14f866"

    event_data = []

    @ha.callback
    def run_callback(event: ha.Event) -> None:
        event_data.append(event.data)

    @ha.callback
    def failing_callback(event: ha.Event) -> None:
        raise ValueError

    unsub1 = async_track_device_registry_updated_event(
        menuai, device_id, failing_callback
    )
    unsub2 = async_track_device_registry_updated_event(menuai, device_id, run_callback)
    menuai.bus.async_fire(
        EVENT_DEVICE_REGISTRY_UPDATED, {"action": "create", "device_id": device_id}
    )
    await menuai.async_block_till_done()
    unsub1()
    unsub2()

    assert event_data[0] == {"action": "create", "device_id": device_id}


async def test_track_state_change_deprecated(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test track_state_change is deprecated."""
    async_track_state_change(
        menuai, "light.Bowl", lambda entity_id, old_state, new_state: None, "on", "off"
    )

    assert (
        "Detected code that calls `async_track_state_change` instead "
        "of `async_track_state_change_event` which is deprecated and "
        "will be removed in MenuAI 2025.5. Please report this issue"
    ) in caplog.text


async def test_track_point_in_time_repr(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test track point in time."""

    @ha.callback
    def _raise_exception(_):
        raise RuntimeError("something happened and its poorly described")

    async_track_point_in_utc_time(menuai, _raise_exception, dt_util.utcnow())
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "Exception in callback _TrackPointUTCTime" in caplog.text
    assert "._raise_exception" in caplog.text
    await menuai.async_block_till_done(wait_background_tasks=True)


async def test_async_track_state_report_event(menuai: menuai) -> None:
    """Test async_track_state_report_event."""
    tracker_called: list[ha.State] = []

    @ha.callback
    def single_run_callback(event: Event[EventStateReportedData]) -> None:
        new_state = event.data["new_state"]
        tracker_called.append(new_state)

    unsub = async_track_state_report_event(
        menuai, ["light.bowl", "light.top"], single_run_callback
    )
    menuai.states.async_set("light.bowl", "on")
    menuai.states.async_set("light.top", "on")
    await menuai.async_block_till_done()
    assert len(tracker_called) == 0
    menuai.states.async_set("light.bowl", "on")
    menuai.states.async_set("light.top", "on")
    await menuai.async_block_till_done()
    assert len(tracker_called) == 2
    unsub()


async def test_async_track_template_no_menuai_deprecated(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test async_track_template with a template without menuai is deprecated."""
    message = (
        "Detected code that calls async_track_template_result with template without "
        "menuai. This will stop working in MenuAI 2025.10, please "
        "report this issue"
    )

    async_track_template(menuai, Template("blah"), lambda x, y, z: None)
    assert message in caplog.text
    caplog.clear()

    async_track_template(menuai, Template("blah", menuai), lambda x, y, z: None)
    assert message not in caplog.text
    caplog.clear()


async def test_async_track_template_result_no_menuai_deprecated(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test async_track_template_result with a template without menuai is deprecated."""
    message = (
        "Detected code that calls async_track_template_result with template without "
        "menuai. This will stop working in MenuAI 2025.10, please "
        "report this issue"
    )

    async_track_template_result(
        menuai, [TrackTemplate(Template("blah"), None)], lambda x, y, z: None
    )
    assert message in caplog.text
    caplog.clear()

    async_track_template_result(
        menuai, [TrackTemplate(Template("blah", menuai), None)], lambda x, y, z: None
    )
    assert message not in caplog.text
    caplog.clear()
