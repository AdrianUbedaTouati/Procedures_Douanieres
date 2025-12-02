# -*- coding: utf-8 -*-
"""
Tool: get_tenders_summary

Obtiene un resumen de las licitaciones públicas disponibles en la base de datos.
"""

from typing import Dict, Any
from .auxiliary.tools_base import ToolDefinition
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="get_tenders_summary",
    description=(
        "Obtiene un resumen de las licitaciones públicas disponibles en la base de datos. "
        "Usa esta herramienta al inicio de una conversación para conocer qué licitaciones hay disponibles, "
        "o cuando el usuario pregunte sobre el estado general de las licitaciones. "
        "Devuelve: lista resumida de las últimas licitaciones con ID, título, organismo, presupuesto y fecha."
    ),
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": 'Número máximo de licitaciones a incluir en el resumen. Si no se especifica, devuelve TODAS las licitaciones disponibles.',
                "minimum": 1
            }
        },
        "required": []  # limit es opcional (None = todas)
    },
    function=None,
    category="context"
)


# ============================================================================
# IMPLEMENTACIÓN
# ============================================================================

def get_tenders_summary(limit: int = None, user=None, **kwargs) -> Dict[str, Any]:
    """
    Obtiene un resumen de las licitaciones disponibles.

    Args:
        limit: Número máximo de licitaciones a incluir (default: None = todas)
        user: Instancia del modelo User de Django (opcional)
        **kwargs: Argumentos adicionales

    Returns:
        Dict con resumen de licitaciones formateado
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

        logger.info(f"[GET_TENDERS_SUMMARY] Obteniendo resumen: limit={limit}")

        # Obtener licitaciones que tienen parsed_summary
        tenders_query = Tender.objects.exclude(
            parsed_summary={}
        ).exclude(
            parsed_summary__isnull=True
        ).order_by('-publication_date')

        # Aplicar límite solo si se especifica
        if limit is not None:
            limit = max(limit, 1)  # Mínimo 1
            tenders = tenders_query[:limit]
        else:
            tenders = tenders_query

        if not tenders.exists():
            return {
                'success': False,
                'data': None,
                'error': 'No hay licitaciones indexadas en la base de datos.'
            }

        # Construir resumen
        total_count = tenders.count()
        if limit is not None:
            summary_parts = [
                f"RESUMEN DE LICITACIONES DISPONIBLES ({total_count} más recientes de {tenders_query.count()} totales):",
                ""
            ]
        else:
            summary_parts = [
                f"RESUMEN DE TODAS LAS LICITACIONES DISPONIBLES ({total_count} licitaciones):",
                ""
            ]

        tenders_list = []
        for idx, tender in enumerate(tenders, 1):
            parsed = tender.parsed_summary

            # Extraer datos de REQUIRED y OPTIONAL
            required = parsed.get('REQUIRED', {})
            optional = parsed.get('OPTIONAL', {})

            # Datos esenciales
            ojs_id = required.get('ojs_notice_id', 'N/A')
            title = required.get('title', 'Sin título')[:80]
            buyer = required.get('buyer_name', 'N/A')[:50]
            cpv = required.get('cpv_main', 'N/A')
            budget = optional.get('budget_eur', 'N/A')
            deadline = optional.get('tender_deadline_date', 'N/A')

            # Formatear presupuesto
            if isinstance(budget, (int, float)):
                budget_str = f"€{budget:,.0f}"
            else:
                budget_str = str(budget)

            tender_summary = (
                f"{idx}. ID: {ojs_id}\n"
                f"   Título: {title}\n"
                f"   Organismo: {buyer}\n"
                f"   CPV: {cpv}\n"
                f"   Presupuesto: {budget_str}\n"
                f"   Plazo: {deadline}"
            )

            summary_parts.append(tender_summary)
            summary_parts.append("")

            # También guardar datos estructurados
            tenders_list.append({
                'ojs_notice_id': ojs_id,
                'title': required.get('title', 'Sin título'),
                'buyer_name': buyer,
                'cpv_main': cpv,
                'budget_eur': budget,
                'tender_deadline_date': deadline,
                'publication_date': required.get('publication_date', 'N/A')
            })

        summary_parts.append(f"Total de licitaciones en base de datos: {tenders.count()}")
        summary_parts.append("Para información detallada de alguna licitación, usa las herramientas de búsqueda específicas.")

        formatted_summary = "\n".join(summary_parts)

        logger.info(f"[GET_TENDERS_SUMMARY] ✓ Resumen generado: {total_count} licitaciones")

        return {
            'success': True,
            'data': {
                'formatted_summary': formatted_summary,
                'tenders_list': tenders_list,
                'total_count': tenders.count()
            }
        }

    except Exception as e:
        logger.error(f"[GET_TENDERS_SUMMARY] Error: {e}", exc_info=True)
        return {
            'success': False,
            'data': None,
            'error': f'Error al obtener resumen de licitaciones: {str(e)}'
        }


TOOL_DEFINITION.function = get_tenders_summary
