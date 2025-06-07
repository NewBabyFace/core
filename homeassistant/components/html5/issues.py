"""Issues utility for HTML5."""

import logging

from menuai.core import DOMAIN as menuai_DOMAIN, menuai, callback
from menuai.helpers.issue_registry import IssueSeverity, async_create_issue

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SUCCESSFUL_IMPORT_TRANSLATION_KEY = "deprecated_yaml"
FAILED_IMPORT_TRANSLATION_KEY = "deprecated_yaml_import_issue"

INTEGRATION_TITLE = "HTML5 Push Notifications"


@callback
def async_create_html5_issue(menuai: menuai, import_success: bool) -> None:
    """Create issues for HTML5."""
    if import_success:
        async_create_issue(
            menuai,
            menuai_DOMAIN,
            f"deprecated_yaml_{DOMAIN}",
            breaks_in_ha_version="2025.4.0",
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
            translation_placeholders={
                "domain": DOMAIN,
                "integration_title": INTEGRATION_TITLE,
            },
        )
    else:
        async_create_issue(
            menuai,
            DOMAIN,
            f"deprecated_yaml_{DOMAIN}",
            breaks_in_ha_version="2025.4.0",
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_yaml_import_issue",
            translation_placeholders={
                "domain": DOMAIN,
                "integration_title": INTEGRATION_TITLE,
            },
        )
