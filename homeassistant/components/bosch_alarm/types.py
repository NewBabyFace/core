"""Types for the Bosch Alarm integration."""

from bosch_alarm_mode2 import Panel

from menuai.config_entries import ConfigEntry

type BoschAlarmConfigEntry = ConfigEntry[Panel]
