"""Adds constants for SQL integration."""

import re

from menuai.const import Platform

DOMAIN = "sql"
PLATFORMS = [Platform.SENSOR]

CONF_COLUMN_NAME = "column"
CONF_QUERY = "query"
DB_URL_RE = re.compile("//.*:.*@")
