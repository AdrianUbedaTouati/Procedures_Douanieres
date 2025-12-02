# -*- coding: utf-8 -*-
"""
Tool: find_by_budget

Busca licitaciones por rango de presupuesto.
"""

from typing import Dict, Any
from .base import ToolDefinition
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="find_by_budget",
    description=(
        "Busca licitaciones por presupuesto/dinero. "
        "Usa esta función cuando el usuario mencione CANTIDADES DE DINERO, presupuesto, o quiera licitaciones caras/baratas. "
        "Ejemplos: 'con más de 500k euros', 'la más cara', 'menos de un millón'. "
        "Devuelve las licitaciones ordenadas por presupuesto de mayor a menor."
    ),
    parameters={
        "type": "object",
        "properties": {
            "min_euros": {
                "type": "number",
                "description": 'Presupuesto mínimo en euros. Si el usuario dice "más de 100k", pon 100000 aquí. Si no menciona mínimo, NO uses este parámetro'
            },
            "max_euros": {
                "type": "number",
                "description": 'Presupuesto máximo en euros. Si el usuario dice "menos de 500k", pon 500000 aquí. Si no menciona máximo, NO uses este parámetro'
            },
            "limit": {
                "type": "integer",
                "description": 'Número de licitaciones a devolver. Ajusta según la necesidad: usa 10-15 para búsquedas estándar, 30-50 para análisis exhaustivos. Por defecto: 10',
                "default": 10,
                "minimum": 1,
                "maximum": 100
            }
        }
    },
    function=None,
    category="search"
)


# ============================================================================
# IMPLEMENTACIÓN
# ============================================================================

def find_by_budget(min_euros: float = None, max_euros: float = None, limit: int = 10, db_session=None, **kwargs) -> Dict[str, Any]:
    """
    Busca licitaciones por rango de presupuesto.

    Args:
        min_euros: Presupuesto mínimo en EUR
        max_euros: Presupuesto máximo en EUR
        limit: Número máximo de resultados (default: 10)
        db_session: Sesión de base de datos Django (opcional)
        **kwargs: Argumentos adicionales

    Returns:
        Dict con resultados ordenados por presupuesto DESC
    """
    try:
        # Setup Django si es necesario
        import django
        if not django.apps.apps.ready:
            import os
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
            django.setup()

        from apps.tenders.models import Tender

        logger.info(f"[FIND_BY_BUDGET] Buscando: min={min_euros}, max={max_euros}, limit={limit}")

        # Query a la base de datos
        queryset = Tender.objects.exclude(budget_amount__isnull=True)

        # Aplicar filtros
        if min_euros is not None:
            queryset = queryset.filter(budget_amount__gte=min_euros)
        if max_euros is not None:
            queryset = queryset.filter(budget_amount__lte=max_euros)

        # Ordenar y limitar
        tenders = queryset.order_by('-budget_amount')[:limit]

        if not tenders.exists():
            return {
                'success': True,
                'count': 0,
                'results': [],
                'message': 'No se encontraron licitaciones con los criterios de presupuesto especificados'
            }

        # Formatear resultados
        results = []
        for tender in tenders:
            result = {
                'id': tender.ojs_notice_id,
                'title': tender.title,
                'budget': float(tender.budget_amount),
                'currency': tender.currency,
                'buyer': tender.buyer_name,
            }

            # Campos opcionales
            if tender.deadline:
                result['deadline'] = tender.deadline.isoformat()
            if tender.publication_date:
                result['published'] = tender.publication_date.isoformat()
            if tender.cpv_codes:
                result['cpv'] = tender.cpv_codes
            if tender.contract_type:
                result['contract_type'] = tender.contract_type

            results.append(result)

        # Construir mensaje informativo
        msg_parts = [f'Encontradas {len(results)} licitaciones']
        if min_euros is not None:
            msg_parts.append(f'presupuesto mínimo {min_euros}€')
        if max_euros is not None:
            msg_parts.append(f'presupuesto máximo {max_euros}€')

        logger.info(f"[FIND_BY_BUDGET] ✓ {len(results)} licitaciones encontradas")

        return {
            'success': True,
            'count': len(results),
            'results': results,
            'message': ' con '.join(msg_parts) if len(msg_parts) > 1 else msg_parts[0]
        }

    except Exception as e:
        logger.error(f"[FIND_BY_BUDGET] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


TOOL_DEFINITION.function = find_by_budget
