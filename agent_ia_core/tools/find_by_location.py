# -*- coding: utf-8 -*-
"""
Tool: find_by_location

Busca licitaciones por ubicación geográfica (códigos NUTS).
"""

from typing import Dict, Any
from .base import ToolDefinition
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="find_by_location",
    description=(
        "Busca licitaciones por ubicación geográfica usando códigos NUTS. "
        "Usa esta función cuando el usuario busque licitaciones en una región, ciudad, o país específico. "
        "Ejemplos: 'Madrid', 'Cataluña', 'España'. "
        "Los códigos NUTS son jerárquicos: 'ES' (España), 'ES3' (Madrid), 'ES51' (Cataluña)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": 'Ubicación o código NUTS. Puede ser nombre de región (ej: "Madrid", "Cataluña", "España") o código NUTS directo (ej: "ES3", "ES51"). Para toda España usa "ES"'
            },
            "limit": {
                "type": "integer",
                "description": 'Número de licitaciones a devolver filtradas por ubicación. Ajusta según análisis: 10-15 para regiones específicas, 30+ para análisis territorial amplio. Por defecto: 10',
                "default": 10,
                "minimum": 1,
                "maximum": 100
            }
        },
        "required": ["location"]
    },
    function=None,
    category="search"
)


# ============================================================================
# IMPLEMENTACIÓN
# ============================================================================

def find_by_location(location: str, limit: int = 10, retriever=None, **kwargs) -> Dict[str, Any]:
    """
    Busca licitaciones por ubicación geográfica.

    Args:
        location: Código NUTS o nombre de región/ciudad. Ej: "ES3" para Madrid, "ES" para España
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

        logger.info(f"[FIND_BY_LOCATION] Buscando: location={location}, limit={limit}")

        # Normalizar ubicación a código NUTS si es posible
        location_map = {
            'españa': 'ES',
            'spain': 'ES',
            'madrid': 'ES3',
            'cataluña': 'ES51',
            'catalunya': 'ES51',
            'barcelona': 'ES51',
            'valencia': 'ES52',
            'andalucia': 'ES6',
            'andalucía': 'ES6',
            'pais vasco': 'ES2',
            'país vasco': 'ES2',
            'galicia': 'ES11'
        }

        search_code = location_map.get(location.lower(), location.upper())

        # Buscar usando el retriever con filtro NUTS
        filters = {'nuts_regions': search_code}

        # Hacer búsqueda genérica pero filtrada por ubicación
        documents = retriever.retrieve(
            query=f"licitaciones ubicación {location}",
            filters=filters,
            k=limit
        )

        if not documents:
            return {
                'success': True,
                'count': 0,
                'results': [],
                'message': f'No se encontraron licitaciones en la ubicación "{location}" (código NUTS: {search_code})'
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
                'location': meta.get('nuts_regions', 'N/A'),
                'preview': doc.page_content[:200]
            }

            # Añadir campos opcionales
            if meta.get('budget_eur'):
                result['budget'] = float(meta.get('budget_eur'))

            if meta.get('tender_deadline_date'):
                result['deadline'] = meta.get('tender_deadline_date')

            if meta.get('cpv_codes'):
                result['cpv_codes'] = meta.get('cpv_codes')

            results.append(result)

        logger.info(f"[FIND_BY_LOCATION] ✓ {len(results)} licitaciones encontradas")

        return {
            'success': True,
            'count': len(results),
            'location_filter': search_code,
            'results': results,
            'message': f'Encontradas {len(results)} licitaciones en "{location}" (NUTS: {search_code})'
        }

    except Exception as e:
        logger.error(f"[FIND_BY_LOCATION] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


TOOL_DEFINITION.function = find_by_location
