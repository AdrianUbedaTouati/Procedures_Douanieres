"""
Tools para el sistema de Function Calling.
Cada tool es una función que el LLM puede llamar para obtener información.
"""

from .base import BaseTool
from .search_tools import (
    FindBestTenderTool,
    FindTopTendersTool,
    FindByBudgetTool,
    FindByDeadlineTool,
    FindByCPVTool,
    FindByLocationTool,
    GetStatisticsTool
)
from .tender_tools import (
    GetTenderDetailsTool,
    GetTenderXMLTool,
    CompareTendersTool
)
from .registry import ToolRegistry

__all__ = [
    'BaseTool',
    'FindBestTenderTool',
    'FindTopTendersTool',
    'FindByBudgetTool',
    'FindByDeadlineTool',
    'FindByCPVTool',
    'FindByLocationTool',
    'GetStatisticsTool',
    'GetTenderDetailsTool',
    'GetTenderXMLTool',
    'CompareTendersTool',
    'ToolRegistry'
]
