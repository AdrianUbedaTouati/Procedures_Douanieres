# -*- coding: utf-8 -*-
"""
Tool: find_best_tender

Encuentra LA mejor licitación (singular) más relevante según la consulta del usuario.
Usa análisis de concentración de chunks para determinar relevancia.
"""

from typing import Dict, Any, List, Optional
from .auxiliary.tools_base import ToolDefinition
from .auxiliary.search_base import optimize_and_search_iterative_with_verification
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL (exported como TOOL_DEFINITION)
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="find_best_tender",
    description=(
        "Encuentra LA MEJOR licitación mediante 5 búsquedas secuenciales optimizadas en ChromaDB con verificación de contenido. "
        "Cada búsqueda obtiene el documento completo para validar correspondencia real (no solo chunks). "
        "Analiza chunk_count (1=poco fiable, 2+=fiable) y contenido verificado para seleccionar el mejor documento. "
        "Usa contexto empresarial, historial conversacional y tool calls previas para optimizar búsquedas."
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

def find_best_tender(
    query: str,
    retriever=None,
    llm=None,
    user=None,
    conversation_history: Optional[List[Dict]] = None,
    tool_calls_history: Optional[List[Dict]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Encuentra LA mejor licitación con 5 búsquedas secuenciales optimizadas y verificación de contenido.

    Args:
        query: Consulta de búsqueda semántica
        retriever: Retriever de ChromaDB (inyectado)
        llm: Instancia del LLM (inyectado)
        user: Usuario de Django (inyectado)
        conversation_history: Historial de mensajes del chat (inyectado)
        tool_calls_history: Historial de tool calls (inyectado)
        **kwargs: Argumentos adicionales

    Returns:
        Dict con formato:
        {
            'success': bool,
            'count': int (0 o 1),
            'result': dict | None,
            'message': str,
            'search_metrics': {...}
        }
    """
    try:
        if not retriever:
            return {
                'success': False,
                'error': 'Retriever no disponible',
                'message': 'No se pudo realizar la búsqueda'
            }

        logger.info(f"[FIND_BEST_TENDER] Iniciando búsqueda iterativa para: '{query[:50]}...'")

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
            mode="single"  # Solo 1 documento
        )

        if not search_result['success'] or not search_result['best_documents']:
            clarification = search_result['analysis'].get('clarification_request')
            return {
                'success': True,
                'count': 0,
                'result': None,
                'message': f'No se encontraron licitaciones para "{query}"',
                'clarification_needed': clarification
            }

        # Mejor documento seleccionado
        document = search_result['best_documents'][0]
        analysis = search_result['analysis']

        # Formatear resultado
        result = {
            'id': document['id'],
            'buyer': document['metadata'].get('buyer_name', 'N/A'),
            'chunk_count': document['chunk_count'],
            'score': document['best_score'],
            'preview': document['content'][:300],
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

        # Construir mensaje con métricas
        base_msg = f'Licitación más relevante: {result["id"]} (concentración: {result["chunk_count"]}/7 chunks)'

        # Advertencia si no es fiable
        if not analysis['is_reliable'] and analysis.get('clarification_request'):
            base_msg += f'\n\n⚠️ ADVERTENCIA: {analysis["clarification_request"]}'

        # Métricas de búsqueda
        chunk_prog = analysis.get('chunk_progression', {})
        doc_progression = chunk_prog.get(result['id'], [])
        if doc_progression:
            base_msg += f'\n\n📊 Análisis: {analysis["total_searches"]} búsquedas realizadas, {analysis["unique_documents"]} documentos únicos encontrados.'
            base_msg += f'\nDocumento apareció en {analysis["best_doc_appearances"]}/{analysis["total_searches"]} búsquedas con evolución de chunks: {doc_progression}'

        logger.info(f"[FIND_BEST_TENDER] ✓ Licitación encontrada: {result['id']} "
                   f"(confianza: {analysis['confidence_score']}, fiable: {analysis['is_reliable']})")

        return {
            'success': True,
            'count': 1,
            'result': result,
            'message': base_msg,
            'algorithm': 'iterative_search_5x_with_verification',
            'search_metrics': {
                'iterations': analysis['total_searches'],
                'unique_docs_found': analysis['unique_documents'],
                'best_doc_appearances': analysis['best_doc_appearances'],
                'chunk_progression': doc_progression,
                'confidence': analysis['confidence_score'],
                'is_reliable': analysis['is_reliable'],
                'reasoning': analysis.get('reasoning')
            }
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
