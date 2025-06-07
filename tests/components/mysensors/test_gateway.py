"""Test function in gateway.py."""

from unittest.mock import patch

import pytest
import voluptuous as vol

from menuai.components.mysensors.gateway import is_serial_port
from menuai.core import menuai


@pytest.mark.parametrize(
    ("port", "expect_valid"),
    [
        ("COM5", True),
        ("asdf", False),
        ("COM17", True),
        ("COM", False),
        ("/dev/ttyACM0", False),
    ],
)
def test_is_serial_port_windows(
    menuai: menuai, port: str, expect_valid: bool
) -> None:
    """Test windows serial port."""

    with patch("sys.platform", "win32"):
        try:
            is_serial_port(port)
        except vol.Invalid:
            assert not expect_valid
        else:
            assert expect_valid
