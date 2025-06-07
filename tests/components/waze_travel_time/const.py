"""Constants for waze_travel_time tests."""

from menuai.components.waze_travel_time.const import (
    CONF_DESTINATION,
    CONF_ORIGIN,
)
from menuai.const import CONF_REGION

MOCK_CONFIG = {
    CONF_ORIGIN: "location1",
    CONF_DESTINATION: "location2",
    CONF_REGION: "US",
}

CONFIG_FLOW_USER_INPUT = {
    CONF_ORIGIN: "location1",
    CONF_DESTINATION: "location2",
    CONF_REGION: "us",
}
