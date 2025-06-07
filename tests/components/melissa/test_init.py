"""The test for the Melissa Climate component."""

from menuai.core import menuai

from . import setup_integration


async def test_setup(menuai: menuai, mock_melissa) -> None:
    """Test setting up the Melissa component."""
    await setup_integration(menuai)

    mock_melissa.assert_called_with(username="********", password="********")
