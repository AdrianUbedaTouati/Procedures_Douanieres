"""
Funciones auxiliares compartidas entre múltiples tools.

Este módulo NO contiene tools, solo funciones utilit

arias que las tools pueden reutilizar.
"""

from .search_base import semantic_search_single, semantic_search_multiple
from .formatting import format_tender_summary, format_search_results

__all__ = [
    'semantic_search_single',
    'semantic_search_multiple',
    'format_tender_summary',
    'format_search_results'
]
