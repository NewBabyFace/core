"""Configure and test MatrixBot."""

from menuai.components.matrix import MatrixBot
from menuai.components.matrix.const import DOMAIN, SERVICE_SEND_MESSAGE
from menuai.components.notify import DOMAIN as NOTIFY_DOMAIN
from menuai.core import menuai

from .conftest import TEST_NOTIFIER_NAME


async def test_services(menuai: menuai, matrix_bot: MatrixBot) -> None:
    """Test menuai/MatrixBot state."""

    services = menuai.services.async_services()

    # Verify that the matrix service is registered
    assert (matrix_service := services.get(DOMAIN))
    assert SERVICE_SEND_MESSAGE in matrix_service

    # Verify that the matrix notifier is registered
    assert (notify_service := services.get(NOTIFY_DOMAIN))
    assert TEST_NOTIFIER_NAME in notify_service
