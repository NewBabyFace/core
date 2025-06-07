"""The test for the bayesian sensor platform."""

import json
from logging import WARNING
from unittest.mock import patch

import pytest

from menuai import config as menuai_config
from menuai.components.bayesian import DOMAIN, binary_sensor as bayesian
from menuai.components.menuai import (
    DOMAIN as HA_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_RELOAD,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from menuai.core import Context, menuai, callback
from menuai.helpers import issue_registry as ir
from menuai.helpers.event import async_track_state_change_event
from menuai.setup import async_setup_component

from tests.common import get_fixture_path


async def test_load_values_when_added_to_menuai(menuai: menuai) -> None:
    """Test that sensor initializes with observations of relevant entities."""

    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "unique_id": "3b4c9563-5e84-4167-8fe7-8f507e796d72",
            "device_class": "connectivity",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "sensor.test_monitored",
                    "to_state": "off",
                    "prob_given_true": 0.8,
                    "prob_given_false": 0.4,
                }
            ],
            "prior": 0.2,
            "probability_threshold": 0.32,
        }
    }

    menuai.states.async_set("sensor.test_monitored", "off")
    await menuai.async_block_till_done()

    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert state.attributes.get("device_class") == "connectivity"
    assert state.attributes.get("observations")[0]["prob_given_true"] == 0.8
    assert state.attributes.get("observations")[0]["prob_given_false"] == 0.4


async def test_unknown_state_does_not_influence_probability(
    menuai: menuai,
) -> None:
    """Test that an unknown state does not change the output probability."""
    prior = 0.2
    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "sensor.test_monitored",
                    "to_state": "off",
                    "prob_given_true": 0.8,
                    "prob_given_false": 0.4,
                }
            ],
            "prior": prior,
            "probability_threshold": 0.32,
        }
    }
    menuai.states.async_set("sensor.test_monitored", "on")
    await menuai.async_block_till_done()
    menuai.states.async_set("sensor.test_monitored", STATE_UNKNOWN)
    await menuai.async_block_till_done()

    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert state.attributes.get("occurred_observation_entities") == []
    assert state.attributes.get("probability") == prior


async def test_sensor_numeric_state(
    menuai: menuai, issue_registry: ir.IssueRegistry
) -> None:
    """Test sensor on numeric state platform observations."""
    config = {
        "binary_sensor": {
            "platform": "bayesian",
            "name": "Test_Binary",
            "observations": [
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.test_monitored",
                    "below": 10,
                    "above": 5,
                    "prob_given_true": 0.7,
                    "prob_given_false": 0.4,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.test_monitored1",
                    "below": 7,
                    "above": 5,
                    "prob_given_true": 0.9,
                    "prob_given_false": 0.2,
                },
            ],
            "prior": 0.2,
        }
    }

    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test_monitored", 6)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")

    assert state.attributes.get("occurred_observation_entities") == [
        "sensor.test_monitored"
    ]
    assert abs(state.attributes.get("probability") - 0.304) < 0.01
    # A = sensor.test_binary being ON
    # B = sensor.test_monitored in the range [5, 10]
    # Bayes theorum  is P(A|B) = P(B|A) * P(A) / P(B|A)*P(A) + P(B|~A)*P(~A).
    # Where P(B|A) is prob_given_true and P(B|~A) is prob_given_false
    # Calculated using P(A) = 0.2, P(B|A) = 0.7, P(B|~A) = 0.4 -> 0.30

    menuai.states.async_set("sensor.test_monitored", 4)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")

    assert state.attributes.get("occurred_observation_entities") == [
        "sensor.test_monitored"
    ]
    assert abs(state.attributes.get("probability") - 0.111) < 0.01
    # As abve but since the value is equal to 4 then this is a negative observation (~B) where P(~B) == 1 - P(B) because B is binary
    # We therefore want to calculate P(A|~B) so we use P(~B|A) (1-0.7) and P(~B|~A) (1-0.4)
    # Calculated using bayes theorum where P(A) = 0.2, P(~B|A) = 1-0.7 (as negative observation), P(~B|notA) = 1-0.4 -> 0.11

    assert state.state == "off"

    menuai.states.async_set("sensor.test_monitored", 6)
    await menuai.async_block_till_done()
    menuai.states.async_set("sensor.test_monitored1", 6)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert state.attributes.get("observations")[0]["prob_given_true"] == 0.7
    assert state.attributes.get("observations")[1]["prob_given_true"] == 0.9
    assert state.attributes.get("observations")[1]["prob_given_false"] == 0.2
    assert abs(state.attributes.get("probability") - 0.663) < 0.01
    # Here we have two positive observations as both are in range. We do a 2-step bayes. The output of the first is used as the (updated) prior in the second.
    # 1st step P(A) = 0.2, P(B|A) = 0.7, P(B|notA) = 0.4 -> 0.304
    # 2nd update: P(A) = 0.304, P(B|A) = 0.9, P(B|notA) = 0.2 -> 0.663

    assert state.state == "on"

    menuai.states.async_set("sensor.test_monitored1", 0)
    await menuai.async_block_till_done()
    menuai.states.async_set("sensor.test_monitored", 4)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert abs(state.attributes.get("probability") - 0.0153) < 0.01
    # Calculated using bayes theorum where P(A) = 0.2, P(~B|A) = 0.3, P(~B|notA) = 0.6 -> 0.11
    # 2nd update: P(A) = 0.111, P(~B|A) = 0.1, P(~B|notA) = 0.8

    assert state.state == "off"

    menuai.states.async_set("sensor.test_monitored", 15)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")

    assert state.state == "off"

    assert len(issue_registry.issues) == 0


async def test_sensor_state(menuai: menuai) -> None:
    """Test sensor on state platform observations."""
    prior = 0.2
    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "sensor.test_monitored",
                    "to_state": "off",
                    "prob_given_true": 0.8,
                    "prob_given_false": 0.4,
                }
            ],
            "prior": prior,
            "probability_threshold": 0.32,
        }
    }

    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test_monitored", "on")
    await menuai.async_block_till_done()
    state = menuai.states.get("binary_sensor.test_binary")

    assert state.attributes.get("occurred_observation_entities") == [
        "sensor.test_monitored"
    ]
    assert state.attributes.get("observations")[0]["prob_given_true"] == 0.8
    assert state.attributes.get("observations")[0]["prob_given_false"] == 0.4
    assert abs(0.0769 - state.attributes.get("probability")) < 0.01
    # Calculated using bayes theorum where P(A) = 0.2, P(~B|A) = 0.2 (as negative observation), P(~B|notA) = 0.6
    assert state.state == "off"

    menuai.states.async_set("sensor.test_monitored", "off")
    await menuai.async_block_till_done()
    state = menuai.states.get("binary_sensor.test_binary")

    assert state.attributes.get("occurred_observation_entities") == [
        "sensor.test_monitored"
    ]
    assert abs(0.33 - state.attributes.get("probability")) < 0.01
    # Calculated using bayes theorum where P(A) = 0.2, P(~B|A) = 0.8 (as negative observation), P(~B|notA) = 0.4
    assert state.state == "on"

    menuai.states.async_remove("sensor.test_monitored")
    await menuai.async_block_till_done()
    state = menuai.states.get("binary_sensor.test_binary")

    assert state.attributes.get("occurred_observation_entities") == []
    assert abs(prior - state.attributes.get("probability")) < 0.01
    assert state.state == "off"

    menuai.states.async_set("sensor.test_monitored", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()
    state = menuai.states.get("binary_sensor.test_binary")

    assert state.attributes.get("occurred_observation_entities") == []
    assert abs(prior - state.attributes.get("probability")) < 0.01
    assert state.state == "off"

    menuai.states.async_set("sensor.test_monitored", STATE_UNKNOWN)
    await menuai.async_block_till_done()
    state = menuai.states.get("binary_sensor.test_binary")

    assert state.attributes.get("occurred_observation_entities") == []
    assert abs(prior - state.attributes.get("probability")) < 0.01
    assert state.state == "off"


async def test_sensor_value_template(menuai: menuai) -> None:
    """Test sensor on template platform observations."""
    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "template",
                    "value_template": "{{states('sensor.test_monitored') == 'off'}}",
                    "prob_given_true": 0.8,
                    "prob_given_false": 0.4,
                }
            ],
            "prior": 0.2,
            "probability_threshold": 0.32,
        }
    }

    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test_monitored", "on")

    state = menuai.states.get("binary_sensor.test_binary")

    assert state.attributes.get("occurred_observation_entities") == []
    assert abs(0.0769 - state.attributes.get("probability")) < 0.01
    # Calculated using bayes theorum where P(A) = 0.2, P(~B|A) = 0.2 (as negative observation), P(~B|notA) = 0.6

    assert state.state == "off"

    menuai.states.async_set("sensor.test_monitored", "off")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert state.attributes.get("observations")[0]["prob_given_true"] == 0.8
    assert state.attributes.get("observations")[0]["prob_given_false"] == 0.4
    assert abs(0.33333 - state.attributes.get("probability")) < 0.01
    # Calculated using bayes theorum where P(A) = 0.2, P(B|A) = 0.8, P(B|notA) = 0.4

    assert state.state == "on"

    menuai.states.async_set("sensor.test_monitored", "on")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert abs(0.076923 - state.attributes.get("probability")) < 0.01
    # Calculated using bayes theorum where P(A) = 0.2, P(~B|A) = 0.2 (as negative observation), P(~B|notA) = 0.6

    assert state.state == "off"


async def test_mixed_states(menuai: menuai) -> None:
    """Test sensor on probability threshold limits."""
    config = {
        "binary_sensor": {
            "name": "should_HVAC",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "template",
                    "value_template": "{{states('sensor.guest_sensor') != 'off'}}",
                    "prob_given_true": 0.3,
                    "prob_given_false": 0.15,
                },
                {
                    "platform": "state",
                    "entity_id": "sensor.anyone_home",
                    "to_state": "on",
                    "prob_given_true": 0.6,
                    "prob_given_false": 0.05,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.temperature",
                    "below": 24,
                    "above": 19,
                    "prob_given_true": 0.1,
                    "prob_given_false": 0.6,
                },
            ],
            "prior": 0.3,
            "probability_threshold": 0.5,
        }
    }
    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.guest_sensor", "UNKNOWN")
    menuai.states.async_set("sensor.anyone_home", "on")
    menuai.states.async_set("sensor.temperature", 15)

    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.should_HVAC")

    assert set(state.attributes.get("occurred_observation_entities")) == {
        "sensor.anyone_home",
        "sensor.temperature",
    }
    template_obs = {
        "platform": "template",
        "value_template": "{{states('sensor.guest_sensor') != 'off'}}",
        "prob_given_true": 0.3,
        "prob_given_false": 0.15,
        "observed": True,
    }
    assert template_obs in state.attributes.get("observations")

    assert abs(0.95857988 - state.attributes.get("probability")) < 0.01
    # A = binary_sensor.should_HVAC being TRUE, P(A) being the prior
    # B = value_template evaluating to TRUE
    # Bayes theorum  is P(A|B) = P(B|A) * P(A) / ( P(B|A)*P(A) + P(B|~A)*P(~A) ).
    # Calculated where P(A) = 0.3, P(B|A) = 0.3 , P(B|notA) = 0.15 = 0.46153846
    # Step 2, prior is now 0.46153846, B now refers to sensor.anyone_home=='on'
    # P(A) = 0.46153846, P(B|A) = 0.6 , P(B|notA) = 0.05, result = 0.91139240
    # Step 3, prior is now 0.91139240, B now refers to sensor.temperature in range [19,24]
    # However since the temp is 15 we take the inverse probability for this negative observation
    # P(A) = 0.91139240, P(B|A) = (1-0.1) , P(B|notA) = (1-0.6), result = 0.95857988


async def test_threshold(menuai: menuai, issue_registry: ir.IssueRegistry) -> None:
    """Test sensor on probability threshold limits."""
    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "sensor.test_monitored",
                    "to_state": "on",
                    "prob_given_true": 1.0,
                    "prob_given_false": 0.0,
                }
            ],
            "prior": 0.5,
            "probability_threshold": 1.0,
        }
    }

    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test_monitored", "on")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert round(abs(1.0 - state.attributes.get("probability")), 7) == 0

    assert state.state == "on"
    assert len(issue_registry.issues) == 0


async def test_multiple_observations(menuai: menuai) -> None:
    """Test sensor with multiple observations of same entity.

    these entries should be labelled as 'state' and negative observations ignored - as the outcome is not known to be binary.
    Before the merge of #67631 this practice was a common work-around for bayesian's ignoring of negative observations,
    this also preserves that function
    """

    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "sensor.test_monitored",
                    "to_state": "blue",
                    "prob_given_true": 0.8,
                    "prob_given_false": 0.4,
                },
                {
                    "platform": "state",
                    "entity_id": "sensor.test_monitored",
                    "to_state": "red",
                    "prob_given_true": 0.2,
                    "prob_given_false": 0.6,
                },
            ],
            "prior": 0.2,
            "probability_threshold": 0.32,
        }
    }

    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test_monitored", "off")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")

    for attrs in state.attributes.values():
        json.dumps(attrs)
    assert state.attributes.get("occurred_observation_entities") == []
    assert state.attributes.get("probability") == 0.2
    # probability should be the same as the prior as negative observations are ignored in multi-state

    assert state.state == "off"

    menuai.states.async_set("sensor.test_monitored", "blue")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")

    assert state.attributes.get("occurred_observation_entities") == [
        "sensor.test_monitored"
    ]
    assert state.attributes.get("observations")[0]["prob_given_true"] == 0.8
    assert state.attributes.get("observations")[0]["prob_given_false"] == 0.4
    assert round(abs(0.33 - state.attributes.get("probability")), 7) == 0
    # Calculated using bayes theorum where P(A) = 0.2, P(B|A) = 0.8, P(B|notA) = 0.4

    assert state.state == "on"

    menuai.states.async_set("sensor.test_monitored", "red")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert abs(0.076923 - state.attributes.get("probability")) < 0.01
    # Calculated using bayes theorum where P(A) = 0.2, P(B|A) = 0.2, P(B|notA) = 0.6

    assert state.state == "off"
    assert state.attributes.get("observations")[0]["platform"] == "state"
    assert state.attributes.get("observations")[1]["platform"] == "state"


async def test_multiple_numeric_observations(
    menuai: menuai, issue_registry: ir.IssueRegistry
) -> None:
    """Test sensor on numeric state platform observations with more than one range.

    This tests an example where the probability of it being a 'nice day' varies over
    a series of temperatures. Since this is a multi-state, all the non-observed ranges
    should be ignored and only the range including the observed value should update
    the prior. When a value lands on above or below (15 is tested) it is included if it
    equals `below`, and ignored if it equals `above`.
    """

    config = {
        "binary_sensor": {
            "platform": "bayesian",
            "name": "nice_day",
            "observations": [
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.test_temp",
                    "below": 0,
                    "prob_given_true": 0.05,
                    "prob_given_false": 0.2,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.test_temp",
                    "below": 10,
                    "above": 0,
                    "prob_given_true": 0.1,
                    "prob_given_false": 0.25,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.test_temp",
                    "below": 15,
                    "above": 10,
                    "prob_given_true": 0.2,
                    "prob_given_false": 0.35,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.test_temp",
                    "below": 25,
                    "above": 15,
                    "prob_given_true": 0.5,
                    "prob_given_false": 0.15,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.test_temp",
                    "above": 25,
                    "prob_given_true": 0.15,
                    "prob_given_false": 0.05,
                },
            ],
            "prior": 0.3,
        }
    }
    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test_temp", -5)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.nice_day")

    for attrs in state.attributes.values():
        json.dumps(attrs)
    assert state.attributes.get("occurred_observation_entities") == ["sensor.test_temp"]
    assert state.attributes.get("probability") == 0.1

    # No observations made so probability should be the prior
    assert state.attributes.get("occurred_observation_entities") == ["sensor.test_temp"]
    assert abs(state.attributes.get("probability") - 0.09677) < 0.01
    # A = binary_sensor.nice_day being TRUE
    # B = sensor.test_temp in the range (, 0]
    # Bayes theorum  is P(A|B) = P(B|A) * P(A) / ( P(B|A)*P(A) + P(B|~A)*P(~A) ).
    # Where P(B|A) is prob_given_true and P(B|~A) is prob_given_false
    # Calculated using P(A) = 0.3, P(B|A) = 0.05, P(B|~A) = 0.2 -> 0.09677
    # Because >1 range is defined for sensor.test_temp we should not infer anything from the
    # ranges not observed
    assert state.state == "off"

    menuai.states.async_set("sensor.test_temp", 5)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.nice_day")

    assert state.attributes.get("occurred_observation_entities") == ["sensor.test_temp"]
    assert abs(state.attributes.get("probability") - 0.14634146) < 0.01
    # A = binary_sensor.nice_day being TRUE
    # B = sensor.test_temp in the range (0, 10]
    # Bayes theorum  is P(A|B) = P(B|A) * P(A) / ( P(B|A)*P(A) + P(B|~A)*P(~A) ).
    # Where P(B|A) is prob_given_true and P(B|~A) is prob_given_false
    # Calculated using P(A) = 0.3, P(B|A) = 0.1, P(B|~A) = 0.25 -> 0.14634146
    # Because >1 range is defined for sensor.test_temp we should not infer anything from the
    # ranges not observed

    assert state.state == "off"

    menuai.states.async_set("sensor.test_temp", 12)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.nice_day")
    assert abs(state.attributes.get("probability") - 0.19672131) < 0.01
    # A = binary_sensor.nice_day being TRUE
    # B = sensor.test_temp in the range (10, 15]
    # Bayes theorum  is P(A|B) = P(B|A) * P(A) / ( P(B|A)*P(A) + P(B|~A)*P(~A) ).
    # Where P(B|A) is prob_given_true and P(B|~A) is prob_given_false
    # Calculated using P(A) = 0.3, P(B|A) = 0.2, P(B|~A) = 0.35 -> 0.19672131
    # Because >1 range is defined for sensor.test_temp we should not infer anything from the
    # ranges not observed

    assert state.state == "off"

    menuai.states.async_set("sensor.test_temp", 22)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.nice_day")
    assert abs(state.attributes.get("probability") - 0.58823529) < 0.01
    # A = binary_sensor.nice_day being TRUE
    # B = sensor.test_temp in the range (15, 25]
    # Bayes theorum  is P(A|B) = P(B|A) * P(A) / ( P(B|A)*P(A) + P(B|~A)*P(~A) ).
    # Where P(B|A) is prob_given_true and P(B|~A) is prob_given_false
    # Calculated using P(A) = 0.3, P(B|A) = 0.5, P(B|~A) = 0.15 -> 0.58823529
    # Because >1 range is defined for sensor.test_temp we should not infer anything from the
    # ranges not observed

    assert state.state == "on"

    menuai.states.async_set("sensor.test_temp", 30)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.nice_day")
    assert abs(state.attributes.get("probability") - 0.562500) < 0.01
    # A = binary_sensor.nice_day being TRUE
    # B = sensor.test_temp in the range (25, ]
    # Bayes theorum  is P(A|B) = P(B|A) * P(A) / ( P(B|A)*P(A) + P(B|~A)*P(~A) ).
    # Where P(B|A) is prob_given_true and P(B|~A) is prob_given_false
    # Calculated using P(A) = 0.3, P(B|A) = 0.15, P(B|~A) = 0.05 -> 0.562500
    # Because >1 range is defined for sensor.test_temp we should not infer anything from the
    # ranges not observed

    assert state.state == "on"

    # Edge cases
    # if on a threshold only one observation should be included and not both
    menuai.states.async_set("sensor.test_temp", 15)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.nice_day")

    assert state.attributes.get("occurred_observation_entities") == ["sensor.test_temp"]

    assert abs(state.attributes.get("probability") - 0.19672131) < 0.01
    # Where there are multi numeric ranges when on the threshold, use below
    # A = binary_sensor.nice_day being TRUE
    # B = sensor.test_temp in the range (10, 15]
    # Bayes theorum  is P(A|B) = P(B|A) * P(A) / ( P(B|A)*P(A) + P(B|~A)*P(~A) ).
    # Where P(B|A) is prob_given_true and P(B|~A) is prob_given_false
    # Calculated using P(A) = 0.3, P(B|A) = 0.2, P(B|~A) = 0.35 -> 0.19672131
    # Because >1 range is defined for sensor.test_temp we should not infer anything from the
    # ranges not observed

    assert state.state == "off"

    assert len(issue_registry.issues) == 0
    assert state.attributes.get("observations")[0]["platform"] == "numeric_state"

    menuai.states.async_set("sensor.test_temp", "badstate")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.nice_day")

    assert state.attributes.get("occurred_observation_entities") == []
    assert state.state == "off"

    menuai.states.async_set("sensor.test_temp", STATE_UNAVAILABLE)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.nice_day")

    assert state.attributes.get("occurred_observation_entities") == []
    assert state.state == "off"

    menuai.states.async_set("sensor.test_temp", STATE_UNKNOWN)
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.nice_day")

    assert state.attributes.get("occurred_observation_entities") == []
    assert state.state == "off"


async def test_mirrored_observations(
    menuai: menuai, issue_registry: ir.IssueRegistry
) -> None:
    """Test whether mirrored entries are detected and appropriate issues are created."""

    config = {
        "binary_sensor": {
            "platform": "bayesian",
            "name": "Test_Binary",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "binary_sensor.test_monitored",
                    "to_state": "on",
                    "prob_given_true": 0.8,
                    "prob_given_false": 0.4,
                },
                {
                    "platform": "state",
                    "entity_id": "binary_sensor.test_monitored",
                    "to_state": "off",
                    "prob_given_true": 0.2,
                    "prob_given_false": 0.59,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.test_monitored1",
                    "above": 5,
                    "prob_given_true": 0.7,
                    "prob_given_false": 0.4,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.test_monitored1",
                    "below": 5,
                    "prob_given_true": 0.3,
                    "prob_given_false": 0.6,
                },
                {
                    "platform": "template",
                    "value_template": "{{states('sensor.test_monitored2') == 'off'}}",
                    "prob_given_true": 0.79,
                    "prob_given_false": 0.4,
                },
                {
                    "platform": "template",
                    "value_template": "{{states('sensor.test_monitored2') == 'on'}}",
                    "prob_given_true": 0.2,
                    "prob_given_false": 0.6,
                },
                {
                    "platform": "state",
                    "entity_id": "sensor.colour",
                    "to_state": "blue",
                    "prob_given_true": 0.33,
                    "prob_given_false": 0.8,
                },
                {
                    "platform": "state",
                    "entity_id": "sensor.colour",
                    "to_state": "green",
                    "prob_given_true": 0.3,
                    "prob_given_false": 0.15,
                },
                {
                    "platform": "state",
                    "entity_id": "sensor.colour",
                    "to_state": "red",
                    "prob_given_true": 0.4,
                    "prob_given_false": 0.05,
                },
            ],
            "prior": 0.1,
        }
    }
    assert len(issue_registry.issues) == 0
    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()
    menuai.states.async_set("sensor.test_monitored2", "on")
    await menuai.async_block_till_done()

    assert len(issue_registry.issues) == 3
    assert (
        issue_registry.issues[
            ("bayesian", "mirrored_entry/Test_Binary/sensor.test_monitored1")
        ]
        is not None
    )


async def test_missing_prob_given_false(
    menuai: menuai, issue_registry: ir.IssueRegistry
) -> None:
    """Test whether missing prob_given_false are detected and appropriate issues are created."""

    config = {
        "binary_sensor": {
            "platform": "bayesian",
            "name": "missingpgf",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "binary_sensor.test_monitored",
                    "to_state": "on",
                    "prob_given_true": 0.8,
                },
                {
                    "platform": "template",
                    "value_template": "{{states('sensor.test_monitored2') == 'off'}}",
                    "prob_given_true": 0.79,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.test_monitored1",
                    "above": 5,
                    "prob_given_true": 0.7,
                },
            ],
            "prior": 0.1,
        }
    }
    assert len(issue_registry.issues) == 0
    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()
    menuai.states.async_set("sensor.test_monitored2", "on")
    await menuai.async_block_till_done()

    assert len(issue_registry.issues) == 3
    assert (
        issue_registry.issues[
            ("bayesian", "no_prob_given_false/missingpgf/sensor.test_monitored1")
        ]
        is not None
    )


async def test_bad_multi_numeric(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test whether missing prob_given_false are detected and appropriate issues are created."""

    config = {
        "binary_sensor": {
            "platform": "bayesian",
            "name": "bins_out",
            "observations": [
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.signal_strength",
                    "above": 10,
                    "prob_given_true": 0.01,
                    "prob_given_false": 0.3,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.signal_strength",
                    "above": 5,
                    "below": 10,
                    "prob_given_true": 0.02,
                    "prob_given_false": 0.5,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.signal_strength",
                    "above": 0,
                    "below": 6,  # overlaps
                    "prob_given_true": 0.07,
                    "prob_given_false": 0.1,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.signal_strength",
                    "above": -10,
                    "below": 0,
                    "prob_given_true": 0.3,
                    "prob_given_false": 0.07,
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.signal_strength",
                    "below": -10,
                    "prob_given_true": 0.6,
                    "prob_given_false": 0.03,
                },
            ],
            "prior": 0.2,
        }
    }
    caplog.clear()
    caplog.set_level(WARNING)

    assert await async_setup_component(menuai, "binary_sensor", config)

    assert "entities must not overlap" in caplog.text


async def test_inverted_numeric(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test whether missing prob_given_false are detected and appropriate logs are created."""

    config = {
        "binary_sensor": {
            "platform": "bayesian",
            "name": "goldilocks_zone",
            "observations": [
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.temp",
                    "above": 23,
                    "below": 20,
                    "prob_given_true": 0.9,
                    "prob_given_false": 0.2,
                },
            ],
            "prior": 0.4,
        }
    }

    assert await async_setup_component(menuai, "binary_sensor", config)
    assert (
        "bayesian numeric state 'above' (23.0) must be less than 'below' (20.0)"
        in caplog.text
    )


async def test_no_value_numeric(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test whether missing prob_given_false are detected and appropriate logs are created."""

    config = {
        "binary_sensor": {
            "platform": "bayesian",
            "name": "goldilocks_zone",
            "observations": [
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.temp",
                    "prob_given_true": 0.9,
                    "prob_given_false": 0.2,
                },
            ],
            "prior": 0.4,
        }
    }

    assert await async_setup_component(menuai, "binary_sensor", config)
    assert "at least one of 'above' or 'below' must be specified" in caplog.text


async def test_probability_updates(menuai: menuai) -> None:
    """Test probability update function."""
    prob_given_true = [0.3, 0.6, 0.8]
    prob_given_false = [0.7, 0.4, 0.2]
    prior = 0.5

    for p_t, p_f in zip(prob_given_true, prob_given_false, strict=False):
        prior = bayesian.update_probability(prior, p_t, p_f)

    assert round(abs(0.720000 - prior), 7) == 0

    prob_given_true = [0.8, 0.3, 0.9]
    prob_given_false = [0.6, 0.4, 0.2]
    prior = 0.7

    for p_t, p_f in zip(prob_given_true, prob_given_false, strict=False):
        prior = bayesian.update_probability(prior, p_t, p_f)

    assert round(abs(0.9130434782608695 - prior), 7) == 0


async def test_observed_entities(menuai: menuai) -> None:
    """Test sensor on observed entities."""
    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "sensor.test_monitored",
                    "to_state": "off",
                    "prob_given_true": 0.9,
                    "prob_given_false": 0.4,
                },
                {
                    "platform": "template",
                    "value_template": (
                        "{{is_state('sensor.test_monitored1','on') and"
                        " is_state('sensor.test_monitored','off')}}"
                    ),
                    "prob_given_true": 0.9,
                    "prob_given_false": 0.1,
                },
            ],
            "prior": 0.2,
            "probability_threshold": 0.32,
        }
    }

    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test_monitored", "on")
    await menuai.async_block_till_done()
    menuai.states.async_set("sensor.test_monitored1", "off")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert state.attributes.get("occurred_observation_entities") == [
        "sensor.test_monitored"
    ]

    menuai.states.async_set("sensor.test_monitored", "off")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert state.attributes.get("occurred_observation_entities") == [
        "sensor.test_monitored"
    ]

    menuai.states.async_set("sensor.test_monitored1", "on")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert sorted(state.attributes.get("occurred_observation_entities")) == [
        "sensor.test_monitored",
        "sensor.test_monitored1",
    ]


async def test_state_attributes_are_serializable(menuai: menuai) -> None:
    """Test sensor on observed entities."""
    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "sensor.test_monitored",
                    "to_state": "off",
                    "prob_given_true": 0.9,
                    "prob_given_false": 0.4,
                },
                {
                    "platform": "template",
                    "value_template": (
                        "{{is_state('sensor.test_monitored1','on') and"
                        " is_state('sensor.test_monitored','off')}}"
                    ),
                    "prob_given_true": 0.9,
                    "prob_given_false": 0.1,
                },
            ],
            "prior": 0.2,
            "probability_threshold": 0.32,
        }
    }

    assert await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test_monitored", "on")
    await menuai.async_block_till_done()
    menuai.states.async_set("sensor.test_monitored1", "off")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert state.attributes.get("occurred_observation_entities") == [
        "sensor.test_monitored"
    ]

    menuai.states.async_set("sensor.test_monitored", "off")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert state.attributes.get("occurred_observation_entities") == [
        "sensor.test_monitored"
    ]

    menuai.states.async_set("sensor.test_monitored1", "on")
    await menuai.async_block_till_done()

    state = menuai.states.get("binary_sensor.test_binary")
    assert sorted(state.attributes.get("occurred_observation_entities")) == [
        "sensor.test_monitored",
        "sensor.test_monitored1",
    ]

    for attrs in state.attributes.values():
        json.dumps(attrs)


async def test_template_error(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test sensor with template error."""
    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "template",
                    "value_template": "{{ xyz + 1 }}",
                    "prob_given_true": 0.9,
                    "prob_given_false": 0.1,
                },
            ],
            "prior": 0.2,
            "probability_threshold": 0.32,
        }
    }

    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.test_binary").state == "off"

    assert "TemplateError" in caplog.text
    assert "xyz" in caplog.text


async def test_update_request_with_template(menuai: menuai) -> None:
    """Test sensor on template platform observations that gets an update request."""
    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "template",
                    "value_template": "{{states('sensor.test_monitored') == 'off'}}",
                    "prob_given_true": 0.8,
                    "prob_given_false": 0.4,
                }
            ],
            "prior": 0.2,
            "probability_threshold": 0.32,
        }
    }

    await async_setup_component(menuai, "binary_sensor", config)
    await async_setup_component(menuai, HA_DOMAIN, {})

    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.test_binary").state == "off"

    await menuai.services.async_call(
        HA_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: "binary_sensor.test_binary"},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.test_binary").state == "off"


async def test_update_request_without_template(menuai: menuai) -> None:
    """Test sensor on template platform observations that gets an update request."""
    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "sensor.test_monitored",
                    "to_state": "off",
                    "prob_given_true": 0.9,
                    "prob_given_false": 0.4,
                },
            ],
            "prior": 0.2,
            "probability_threshold": 0.32,
        }
    }

    await async_setup_component(menuai, "binary_sensor", config)
    await async_setup_component(menuai, HA_DOMAIN, {})

    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test_monitored", "on")
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.test_binary").state == "off"

    await menuai.services.async_call(
        HA_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: "binary_sensor.test_binary"},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert menuai.states.get("binary_sensor.test_binary").state == "off"


async def test_monitored_sensor_goes_away(menuai: menuai) -> None:
    """Test sensor on template platform observations that goes away."""
    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "sensor.test_monitored",
                    "to_state": "on",
                    "prob_given_true": 0.9,
                    "prob_given_false": 0.4,
                },
            ],
            "prior": 0.2,
            "probability_threshold": 0.32,
        }
    }

    await async_setup_component(menuai, "binary_sensor", config)
    await async_setup_component(menuai, HA_DOMAIN, {})

    await menuai.async_block_till_done()

    menuai.states.async_set("sensor.test_monitored", "on")
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.test_binary").state == "on"
    # Calculated using bayes theorum where P(A) = 0.2, P(B|A) = 0.9, P(B|notA) = 0.4 -> 0.36 (>0.32)

    menuai.states.async_remove("sensor.test_monitored")

    await menuai.async_block_till_done()
    assert (
        menuai.states.get("binary_sensor.test_binary").attributes.get("probability")
        == 0.2
    )
    assert menuai.states.get("binary_sensor.test_binary").state == "off"


async def test_reload(menuai: menuai) -> None:
    """Verify we can reload bayesian sensors."""

    config = {
        "binary_sensor": {
            "name": "test",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "sensor.test_monitored",
                    "to_state": "on",
                    "prob_given_true": 0.9,
                    "prob_given_false": 0.4,
                },
            ],
            "prior": 0.2,
            "probability_threshold": 0.32,
        }
    }

    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 1

    assert menuai.states.get("binary_sensor.test")

    yaml_path = get_fixture_path("configuration.yaml", "bayesian")

    with patch.object(menuai_config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 1

    assert menuai.states.get("binary_sensor.test") is None
    assert menuai.states.get("binary_sensor.test2")


async def test_template_triggers(menuai: menuai) -> None:
    """Test sensor with template triggers."""
    menuai.states.async_set("input_boolean.test", STATE_OFF)
    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "template",
                    "value_template": "{{ states.input_boolean.test.state }}",
                    "prob_given_true": 1.0,
                    "prob_given_false": 0.0,
                },
            ],
            "prior": 0.2,
            "probability_threshold": 0.32,
        }
    }

    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.test_binary").state == STATE_OFF

    events = []
    async_track_state_change_event(
        menuai,
        "binary_sensor.test_binary",
        # pylint: disable-next=unnecessary-lambda
        callback(lambda event: events.append(event)),
    )

    context = Context()
    menuai.states.async_set("input_boolean.test", STATE_ON, context=context)
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert events[0].context == context


async def test_state_triggers(menuai: menuai) -> None:
    """Test sensor with state triggers."""
    menuai.states.async_set("sensor.test_monitored", STATE_OFF)

    config = {
        "binary_sensor": {
            "name": "Test_Binary",
            "platform": "bayesian",
            "observations": [
                {
                    "platform": "state",
                    "entity_id": "sensor.test_monitored",
                    "to_state": "off",
                    "prob_given_true": 0.9999,
                    "prob_given_false": 0.9994,
                },
            ],
            "prior": 0.2,
            "probability_threshold": 0.32,
        }
    }
    await async_setup_component(menuai, "binary_sensor", config)
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.test_binary").state == STATE_OFF

    events = []
    async_track_state_change_event(
        menuai,
        "binary_sensor.test_binary",
        # pylint: disable-next=unnecessary-lambda
        callback(lambda event: events.append(event)),
    )

    context = Context()
    menuai.states.async_set("sensor.test_monitored", STATE_ON, context=context)
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert events[0].context == context
