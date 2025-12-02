# -*- coding: utf-8 -*-
"""
Tool: find_best_tender

Encuentra LA mejor licitación (singular) más relevante según la consulta del usuario.
Usa análisis de concentración de chunks para determinar relevancia.
"""

from typing import Dict, Any
from .base import ToolDefinition
from .auxiliary.search_base import semantic_search_single
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL (exported como TOOL_DEFINITION)
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="find_best_tender",
    description=(
        "Encuentra LA MEJOR licitación (singular) para una consulta usando análisis de concentración. "
        "USA ESTA TOOL cuando el usuario pida 'LA mejor', 'LA más relevante', 'cuál es LA que más me conviene', "
        "'cuál me recomiendas', 'LA más interesante'. "
        "Esta herramienta analiza los 7 chunks más relevantes y selecciona el documento con mayor concentración. "
        "Ideal para recomendaciones personalizadas donde solo se necesita UNA respuesta."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "La consulta del usuario. Incluye contexto sobre qué busca y por qué. "
                    "Ejemplo: 'licitación de desarrollo web con presupuesto alto', "
                    "'mejor oportunidad para empresa de construcción en Madrid'"
                )
            }
        },
        "required": ["query"]
    },
    function=None,  # Se asignará después
    category="search"
)


# ============================================================================
# IMPLEMENTACIÓN DE LA FUNCIÓN
# ============================================================================

def find_best_tender(query: str, retriever=None, **kwargs) -> Dict[str, Any]:
    """
    Encuentra la mejor licitación según la query usando concentración de chunks.

    Args:
        query: Consulta de búsqueda semántica
        retriever: Retriever de ChromaDB
        **kwargs: Argumentos adicionales (ignorados)

    Returns:
        Dict con formato:
        {
            'success': bool,
            'count': int (0 o 1),
            'result': dict | None,  # Información de la licitación
            'message': str
        }
    """
    try:
        if not retriever:
            return {
                'success': False,
                'error': 'Retriever no disponible',
                'message': 'No se pudo realizar la búsqueda'
            }

        logger.info(f"[FIND_BEST_TENDER] Buscando para: '{query[:50]}...'")

        # Usar función auxiliar de búsqueda semántica
        search_result = semantic_search_single(query=query, vectorstore=retriever, k=7)

        if not search_result['success']:
            return {
                'success': True,  # La tool ejecutó correctamente, solo que no hay resultados
                'count': 0,
                'result': None,
                'message': f'No se encontraron licitaciones para "{query}"'
            }

        document = search_result['document']

        # Formatear resultado
        result = {
            'id': document['id'],
            'buyer': document['metadata'].get('buyer_name', 'N/A'),
            'chunk_count': document['chunk_count'],
            'score': document['best_score'],
            'preview': document['content'][:300],
            'sections_found': [chunk['content'][:50] for chunk in document.get('chunks', [])[:3]]
        }

        # Añadir campos opcionales desde metadata
        meta = document['metadata']
        if meta.get('budget_eur'):
            result['budget'] = float(meta.get('budget_eur'))
        if meta.get('tender_deadline_date'):
            result['deadline'] = meta.get('tender_deadline_date')
        if meta.get('cpv_codes'):
            result['cpv'] = meta.get('cpv_codes')
        if meta.get('nuts_regions'):
            result['location'] = meta.get('nuts_regions')
        if meta.get('publication_date'):
            result['published'] = meta.get('publication_date')

        logger.info(f"[FIND_BEST_TENDER] ✓ Licitación encontrada: {result['id']} "
                   f"(concentración: {result['chunk_count']}/7 chunks)")

        return {
            'success': True,
            'count': 1,
            'result': result,  # Objeto único (no array)
            'message': f'Licitación más relevante: {result["id"]} (concentración: {result["chunk_count"]}/7 chunks)',
            'algorithm': 'chunk_concentration'
        }

    except Exception as e:
        logger.error(f"[FIND_BEST_TENDER] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': f'Error al buscar licitación: {str(e)}'
        }


# ============================================================================
# ASIGNAR FUNCIÓN A LA DEFINICIÓN
# ============================================================================

TOOL_DEFINITION.function = find_best_tender
