# -*- coding: utf-8 -*-
"""
Tool: find_top_tenders

Encuentra X mejores licitaciones (plural) ordenadas por relevancia.
"""

from typing import Dict, Any, List, Optional
from .auxiliary.tools_base import ToolDefinition
from .auxiliary.search_base import optimize_and_search_iterative_with_verification
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="find_top_tenders",
    description=(
        "Encuentra las X mejores licitaciones mediante 5 búsquedas secuenciales optimizadas en ChromaDB con verificación de contenido. "
        "Cada búsqueda obtiene el documento completo para validar correspondencia real. "
        "Retorna múltiples resultados únicos ordenados por relevancia verificada. "
        "Usa contexto empresarial, historial y tool calls previas para optimizar búsquedas."
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

def find_top_tenders(
    query: str,
    limit: int = 5,
    retriever=None,
    llm=None,
    user=None,
    conversation_history: Optional[List[Dict]] = None,
    tool_calls_history: Optional[List[Dict]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Encuentra top N licitaciones con 5 búsquedas secuenciales optimizadas y verificación de contenido.

    Args:
        query: Consulta de búsqueda
        limit: Número de resultados (default: 5, max: 10)
        retriever: Retriever de ChromaDB (inyectado)
        llm: Instancia del LLM (inyectado)
        user: Usuario de Django (inyectado)
        conversation_history: Historial de mensajes (inyectado)
        tool_calls_history: Historial de tool calls (inyectado)
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

        logger.info(f"[FIND_TOP_TENDERS] Iniciando búsqueda iterativa para top-{limit}: '{query[:50]}...'")

        # Obtener info de empresa
        company_info = None
        if user:
            from .get_company_info import get_company_info
            company_result = get_company_info(user=user)
            if company_result.get('success'):
                company_info = company_result.get('data', {})

        # Realizar búsqueda iterativa con verificación (5 búsquedas secuenciales)
        search_result = optimize_and_search_iterative_with_verification(
            original_query=query,
            conversation_history=conversation_history,
            tool_calls_history=tool_calls_history,
            company_info=company_info,
            vectorstore=retriever,
            llm=llm,
            user=user,
            mode="multiple",  # Múltiples documentos
            limit=limit
        )

        if not search_result['success'] or not search_result['best_documents']:
            clarification = search_result['analysis'].get('clarification_request')
            return {
                'success': True,
                'count': 0,
                'results': [],
                'message': f'No se encontraron licitaciones para "{query}"',
                'clarification_needed': clarification
            }

        documents = search_result['best_documents']
        analysis = search_result['analysis']

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
            if meta.get('publication_date'):
                result['published'] = meta.get('publication_date')

            results.append(result)

        # Construir mensaje con métricas
        base_msg = f'Se encontraron {len(results)} licitaciones relevantes'

        # Advertencia si no es fiable
        if not analysis['is_reliable'] and analysis.get('clarification_request'):
            base_msg += f'\n\n⚠️ ADVERTENCIA: {analysis["clarification_request"]}'

        # Métricas de búsqueda
        base_msg += f'\n\n📊 Análisis: {analysis["total_searches"]} búsquedas realizadas, {analysis["unique_documents"]} documentos únicos encontrados'
        base_msg += f'\nDocumentos seleccionados: {analysis["selected_count"]}/{analysis["unique_documents"]}'

        logger.info(f"[FIND_TOP_TENDERS] ✓ {len(results)} licitaciones encontradas "
                   f"(confianza: {analysis['confidence_score']}, fiable: {analysis['is_reliable']})")

        return {
            'success': True,
            'count': len(results),
            'results': results,
            'message': base_msg,
            'algorithm': 'iterative_search_5x_with_verification',
            'search_metrics': {
                'iterations': analysis['total_searches'],
                'unique_docs_found': analysis['unique_documents'],
                'selected_count': analysis['selected_count'],
                'confidence': analysis['confidence_score'],
                'is_reliable': analysis['is_reliable'],
                'reasoning': analysis.get('reasoning')
            }
        }

    except Exception as e:
        logger.error(f"[FIND_TOP_TENDERS] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


TOOL_DEFINITION.function = find_top_tenders
