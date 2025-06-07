"""Demo platform that has two fake alarm control panels."""

from __future__ import annotations

import datetime

from menuai.components.alarm_control_panel import AlarmControlPanelState
from menuai.components.manual.alarm_control_panel import ManualAlarm
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ARMING_TIME, CONF_DELAY_TIME, CONF_TRIGGER_TIME
from menuai.core import menuai
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Demo config entry."""
    async_add_entities(
        [
            ManualAlarm(
                menuai,
                "Security",
                "demo_alarm_control_panel",
                "1234",
                None,
                True,
                False,
                {
                    AlarmControlPanelState.ARMED_AWAY: {
                        CONF_ARMING_TIME: datetime.timedelta(seconds=5),
                        CONF_DELAY_TIME: datetime.timedelta(seconds=0),
                        CONF_TRIGGER_TIME: datetime.timedelta(seconds=10),
                    },
                    AlarmControlPanelState.ARMED_HOME: {
                        CONF_ARMING_TIME: datetime.timedelta(seconds=5),
                        CONF_DELAY_TIME: datetime.timedelta(seconds=0),
                        CONF_TRIGGER_TIME: datetime.timedelta(seconds=10),
                    },
                    AlarmControlPanelState.ARMED_NIGHT: {
                        CONF_ARMING_TIME: datetime.timedelta(seconds=5),
                        CONF_DELAY_TIME: datetime.timedelta(seconds=0),
                        CONF_TRIGGER_TIME: datetime.timedelta(seconds=10),
                    },
                    AlarmControlPanelState.ARMED_VACATION: {
                        CONF_ARMING_TIME: datetime.timedelta(seconds=5),
                        CONF_DELAY_TIME: datetime.timedelta(seconds=0),
                        CONF_TRIGGER_TIME: datetime.timedelta(seconds=10),
                    },
                    AlarmControlPanelState.DISARMED: {
                        CONF_DELAY_TIME: datetime.timedelta(seconds=0),
                        CONF_TRIGGER_TIME: datetime.timedelta(seconds=10),
                    },
                    AlarmControlPanelState.ARMED_CUSTOM_BYPASS: {
                        CONF_ARMING_TIME: datetime.timedelta(seconds=5),
                        CONF_DELAY_TIME: datetime.timedelta(seconds=0),
                        CONF_TRIGGER_TIME: datetime.timedelta(seconds=10),
                    },
                    AlarmControlPanelState.TRIGGERED: {
                        CONF_ARMING_TIME: datetime.timedelta(seconds=5)
                    },
                },
            )
        ]
    )
