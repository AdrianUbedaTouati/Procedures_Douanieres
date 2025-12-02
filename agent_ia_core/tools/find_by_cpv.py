# -*- coding: utf-8 -*-
"""
Tool: find_by_cpv

Busca licitaciones por código CPV (sector/tipo de contrato).
"""

from typing import Dict, Any
from .auxiliary.tools_base import ToolDefinition
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="find_by_cpv",
    description=(
        "Busca licitaciones por código CPV (Common Procurement Vocabulary) que clasifica el tipo de contrato o sector. "
        "Usa esta función cuando el usuario busque por sector específico o tipo de servicio/producto. "
        "Los códigos CPV son jerárquicos: '72' para IT, '45' para construcción, '80' para educación, etc."
    ),
    parameters={
        "type": "object",
        "properties": {
            "cpv_code": {
                "type": "string",
                "description": 'Código CPV o prefijo. Ejemplos: "72" para IT/software, "45" para construcción, "80" para educación, "85" para salud. Puede ser un código completo o solo los primeros dígitos'
            },
            "limit": {
                "type": "integer",
                "description": 'Número de licitaciones a devolver filtradas por CPV. Ajusta según análisis: 10-15 para sectores específicos, 30+ para análisis de mercado amplio. Por defecto: 10',
                "default": 10,
                "minimum": 1,
                "maximum": 100
            }
        },
        "required": ["cpv_code"]
    },
    function=None,
    category="search"
)


# ============================================================================
# IMPLEMENTACIÓN
# ============================================================================

def find_by_cpv(cpv_code: str, limit: int = 10, retriever=None, **kwargs) -> Dict[str, Any]:
    """
    Busca licitaciones por código CPV.

    Args:
        cpv_code: Código CPV (puede ser prefijo). Ej: "72" para IT, "45" para construcción
        limit: Número de resultados (default: 10)
        retriever: HybridRetriever con soporte de filtros
        **kwargs: Argumentos adicionales

    Returns:
        Dict con resultados de la búsqueda
    """
    try:
        if not retriever:
            return {
                'success': False,
                'error': 'Retriever no inicializado'
            }

        logger.info(f"[FIND_BY_CPV] Buscando: cpv={cpv_code}, limit={limit}")

        # Buscar usando el retriever con filtro CPV
        filters = {'cpv_codes': cpv_code}

        # Hacer búsqueda genérica pero filtrada por CPV
        documents = retriever.retrieve(
            query=f"licitaciones sector CPV {cpv_code}",
            filters=filters,
            k=limit
        )

        if not documents:
            return {
                'success': True,
                'count': 0,
                'results': [],
                'message': f'No se encontraron licitaciones con código CPV que contenga "{cpv_code}"'
            }

        # Formatear resultados
        results = []
        seen_ids = set()

        for doc in documents:
            meta = doc.metadata
            tender_id = meta.get('ojs_notice_id')

            if tender_id in seen_ids:
                continue
            seen_ids.add(tender_id)

            result = {
                'id': tender_id,
                'section': meta.get('section', 'N/A'),
                'buyer': meta.get('buyer_name', 'N/A'),
                'cpv_codes': meta.get('cpv_codes', 'N/A'),
                'preview': doc.page_content[:200]
            }

            # Añadir campos opcionales
            if meta.get('budget_eur'):
                result['budget'] = float(meta.get('budget_eur'))

            if meta.get('tender_deadline_date'):
                result['deadline'] = meta.get('tender_deadline_date')

            if meta.get('nuts_regions'):
                result['location'] = meta.get('nuts_regions')

            results.append(result)

        logger.info(f"[FIND_BY_CPV] ✓ {len(results)} licitaciones encontradas")

        return {
            'success': True,
            'count': len(results),
            'cpv_filter': cpv_code,
            'results': results,
            'message': f'Encontradas {len(results)} licitaciones con CPV que contiene "{cpv_code}"'
        }

    except Exception as e:
        logger.error(f"[FIND_BY_CPV] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


TOOL_DEFINITION.function = find_by_cpv
