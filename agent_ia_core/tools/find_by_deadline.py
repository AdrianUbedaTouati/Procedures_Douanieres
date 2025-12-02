# -*- coding: utf-8 -*-
"""
Tool: find_by_deadline

Busca licitaciones por fecha límite de presentación.
"""

from typing import Dict, Any
from .base import ToolDefinition
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="find_by_deadline",
    description=(
        "Busca licitaciones por fecha límite de presentación. "
        "Usa esta función cuando el usuario pregunte por licitaciones que vencen pronto, "
        "que tienen deadline en un rango de fechas específico, o que ya vencieron. "
        "Ejemplo: 'licitaciones que vencen esta semana', 'con deadline antes del 15 de marzo', 'urgentes'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "date_from": {
                "type": "string",
                "description": 'Fecha inicial en formato YYYY-MM-DD. Ejemplo: "2025-01-20". Si el usuario dice "desde mañana", calcula la fecha y úsala aquí'
            },
            "date_to": {
                "type": "string",
                "description": 'Fecha final en formato YYYY-MM-DD. Ejemplo: "2025-02-15". Si el usuario dice "hasta fin de mes", calcula la fecha y úsala aquí'
            },
            "limit": {
                "type": "integer",
                "description": 'Número de licitaciones a devolver ordenadas por proximidad de deadline. Ajusta según necesidad: 10 para urgentes, 30+ para planificación amplia. Por defecto: 10',
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

def find_by_deadline(date_from: str = None, date_to: str = None, limit: int = 10, db_session=None, **kwargs) -> Dict[str, Any]:
    """
    Busca licitaciones por fecha límite.

    Args:
        date_from: Fecha inicial en formato YYYY-MM-DD (opcional)
        date_to: Fecha final en formato YYYY-MM-DD (opcional)
        limit: Número de resultados (default: 10)
        db_session: Sesión de base de datos Django (opcional)
        **kwargs: Argumentos adicionales

    Returns:
        Dict con resultados ordenados por deadline (más próximas primero)
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
        from datetime import date

        logger.info(f"[FIND_BY_DEADLINE] Buscando: from={date_from}, to={date_to}, limit={limit}")

        # Query a la base de datos
        queryset = Tender.objects.exclude(tender_deadline_date__isnull=True)

        # Aplicar filtros de fecha
        if date_from:
            queryset = queryset.filter(tender_deadline_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(tender_deadline_date__lte=date_to)

        # Ordenar por fecha (más próximas primero)
        tenders = queryset.order_by('tender_deadline_date')[:limit]

        if not tenders.exists():
            return {
                'success': True,
                'count': 0,
                'results': [],
                'message': 'No se encontraron licitaciones con los criterios de fecha especificados'
            }

        # Formatear resultados
        results = []
        for tender in tenders:
            result = {
                'id': tender.ojs_notice_id,
                'title': tender.title,
                'buyer': tender.buyer_name,
                'deadline_date': tender.tender_deadline_date.isoformat() if tender.tender_deadline_date else None
            }

            # Añadir información opcional
            if tender.tender_deadline_time:
                result['deadline_time'] = tender.tender_deadline_time.isoformat()

            if tender.budget_amount:
                result['budget'] = float(tender.budget_amount)
                result['currency'] = tender.currency or 'EUR'

            if tender.cpv_codes:
                result['cpv_codes'] = tender.cpv_codes

            if tender.contract_type:
                result['contract_type'] = tender.contract_type

            # Calcular días restantes
            if tender.tender_deadline_date:
                today = date.today()
                days_left = (tender.tender_deadline_date - today).days
                result['days_remaining'] = days_left
                if days_left < 0:
                    result['status'] = 'expired'
                elif days_left <= 7:
                    result['status'] = 'urgent'
                elif days_left <= 30:
                    result['status'] = 'soon'
                else:
                    result['status'] = 'open'

            results.append(result)

        # Construir mensaje informativo
        msg_parts = [f'Encontradas {len(results)} licitaciones']
        if date_from:
            msg_parts.append(f'desde {date_from}')
        if date_to:
            msg_parts.append(f'hasta {date_to}')

        logger.info(f"[FIND_BY_DEADLINE] ✓ {len(results)} licitaciones encontradas")

        return {
            'success': True,
            'count': len(results),
            'results': results,
            'message': ' '.join(msg_parts)
        }

    except Exception as e:
        logger.error(f"[FIND_BY_DEADLINE] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


TOOL_DEFINITION.function = find_by_deadline
