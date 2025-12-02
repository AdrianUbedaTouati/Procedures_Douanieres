# -*- coding: utf-8 -*-
"""
Tool: find_top_tenders

Encuentra X mejores licitaciones (plural) ordenadas por relevancia.
"""

from typing import Dict, Any
from .base import ToolDefinition
from .auxiliary.search_base import semantic_search_multiple
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="find_top_tenders",
    description=(
        "Encuentra X mejores licitaciones (plural) ordenadas por relevancia usando análisis de concentración. "
        "USA ESTA TOOL cuando el usuario pida 'las mejores', 'varias opciones', 'top 5', 'múltiples licitaciones', "
        "'dame opciones', 'quiero ver varias'. "
        "Retorna una lista ordenada de licitaciones únicas basándose en concentración de chunks."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Consulta de búsqueda semántica"
            },
            "limit": {
                "type": "integer",
                "description": "Número de licitaciones a retornar (máximo 10)",
                "default": 5,
                "minimum": 1,
                "maximum": 10
            }
        },
        "required": ["query"]
    },
    function=None,
    category="search"
)


# ============================================================================
# IMPLEMENTACIÓN
# ============================================================================

def find_top_tenders(query: str, limit: int = 5, retriever=None, **kwargs) -> Dict[str, Any]:
    """
    Encuentra top N licitaciones ordenadas por relevancia.

    Args:
        query: Consulta de búsqueda
        limit: Número de resultados (default: 5, max: 10)
        retriever: Retriever de ChromaDB
        **kwargs: Argumentos adicionales

    Returns:
        Dict con lista de licitaciones encontradas
    """
    try:
        if not retriever:
            return {
                'success': False,
                'error': 'Retriever no disponible'
            }

        # Validar límite
        limit = max(1, min(limit, 10))

        logger.info(f"[FIND_TOP_TENDERS] Buscando top-{limit} para: '{query[:50]}...'")

        # Usar función auxiliar
        search_result = semantic_search_multiple(
            query=query,
            vectorstore=retriever,
            limit=limit,
            k_per_doc=7
        )

        if not search_result['success']:
            return {
                'success': True,
                'count': 0,
                'results': [],
                'message': f'No se encontraron licitaciones para "{query}"'
            }

        documents = search_result['documents']

        # Formatear resultados
        results = []
        for doc in documents:
            result = {
                'id': doc['id'],
                'buyer': doc['metadata'].get('buyer_name', 'N/A'),
                'chunk_count': doc['chunk_count'],
                'score': doc['best_score'],
                'preview': doc['content'][:300]
            }

            # Campos opcionales
            meta = doc['metadata']
            if meta.get('budget_eur'):
                result['budget'] = float(meta.get('budget_eur'))
            if meta.get('tender_deadline_date'):
                result['deadline'] = meta.get('tender_deadline_date')
            if meta.get('cpv_codes'):
                result['cpv'] = meta.get('cpv_codes')
            if meta.get('nuts_regions'):
                result['location'] = meta.get('nuts_regions')

            results.append(result)

        logger.info(f"[FIND_TOP_TENDERS] ✓ {len(results)} licitaciones encontradas")

        return {
            'success': True,
            'count': len(results),
            'results': results,
            'message': f'Se encontraron {len(results)} licitaciones relevantes',
            'algorithm': 'chunk_concentration'
        }

    except Exception as e:
        logger.error(f"[FIND_TOP_TENDERS] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


TOOL_DEFINITION.function = find_top_tenders
