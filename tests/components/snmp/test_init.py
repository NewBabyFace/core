"""SNMP tests."""

from unittest.mock import patch

from pysnmp.hlapi.asyncio import SnmpEngine
from pysnmp.hlapi.asyncio.cmdgen import lcd

from menuai.components import snmp
from menuai.const import EVENT_menuai_STOP
from menuai.core import menuai


async def test_async_get_snmp_engine(menuai: menuai) -> None:
    """Test async_get_snmp_engine."""
    engine = await snmp.async_get_snmp_engine(menuai)
    assert isinstance(engine, SnmpEngine)
    engine2 = await snmp.async_get_snmp_engine(menuai)
    assert engine is engine2
    with patch.object(lcd, "unconfigure") as mock_unconfigure:
        menuai.bus.async_fire(EVENT_menuai_STOP)
        await menuai.async_block_till_done()
    assert mock_unconfigure.called
