# -*- coding: utf-8 -*-
"""
Tool: compare_tenders

Compara múltiples licitaciones lado a lado mostrando diferencias y similitudes.
"""

from typing import Dict, Any, List
from .base import ToolDefinition
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="compare_tenders",
    description=(
        "Compara dos o más licitaciones mostrando diferencias y similitudes en presupuesto, plazos, ubicación, etc. "
        "Usa esta función cuando el usuario quiera comparar licitaciones, ver cuál es mejor, "
        "o analizar diferencias entre opciones. Requiere al menos 2 IDs de licitaciones (máximo 5)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "tender_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": 'Lista de IDs a comparar. Ejemplo: ["12345-2025", "67890-2025"]. Mínimo 2, máximo 5',
                "minItems": 2,
                "maxItems": 5
            }
        },
        "required": ["tender_ids"]
    },
    function=None,
    category="analysis"
)


# ============================================================================
# IMPLEMENTACIÓN
# ============================================================================

def compare_tenders(tender_ids: List[str], db_session=None, **kwargs) -> Dict[str, Any]:
    """
    Compara múltiples licitaciones.

    Args:
        tender_ids: Lista de IDs de licitaciones a comparar
        db_session: Sesión de base de datos Django (opcional)
        **kwargs: Argumentos adicionales

    Returns:
        Dict con comparación detallada de las licitaciones
    """
    try:
        if not tender_ids or len(tender_ids) < 2:
            return {
                'success': False,
                'error': 'Se requieren al menos 2 IDs para comparar'
            }

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

        logger.info(f"[COMPARE_TENDERS] Comparando {len(tender_ids)} licitaciones")

        # Buscar todas las licitaciones
        tenders = []
        for tender_id in tender_ids[:5]:  # Máximo 5
            try:
                tender = Tender.objects.get(ojs_notice_id=tender_id)
                tenders.append(tender)
                logger.info(f"[COMPARE_TENDERS] ✓ Encontrada: {tender_id}")
            except Tender.DoesNotExist:
                logger.warning(f"[COMPARE_TENDERS] ✗ No encontrada: {tender_id}")
                return {
                    'success': False,
                    'error': f'Licitación {tender_id} no encontrada'
                }

        # Construir comparación
        comparison = {
            'count': len(tenders),
            'tenders': [],
            'summary': {}
        }

        budgets = []
        deadlines = []

        for tender in tenders:
            tender_data = {
                'id': tender.ojs_notice_id,
                'title': tender.title,
                'buyer': tender.buyer_name,
                'budget': float(tender.budget_amount) if tender.budget_amount else None,
                'currency': tender.currency or 'EUR',
                'deadline': tender.tender_deadline_date.isoformat() if tender.tender_deadline_date else None,
                'cpv_codes': tender.cpv_codes,
                'location': tender.nuts_regions,
                'contract_type': tender.contract_type
            }

            # Recopilar datos para resumen
            if tender.budget_amount:
                budgets.append(float(tender.budget_amount))
            if tender.tender_deadline_date:
                deadlines.append(tender.tender_deadline_date)

            comparison['tenders'].append(tender_data)

        # Resumen de comparación
        if budgets:
            comparison['summary']['budget_comparison'] = {
                'min': min(budgets),
                'max': max(budgets),
                'avg': sum(budgets) / len(budgets),
                'difference': max(budgets) - min(budgets)
            }

        if deadlines:
            comparison['summary']['deadline_comparison'] = {
                'earliest': min(deadlines).isoformat(),
                'latest': max(deadlines).isoformat()
            }

        logger.info(f"[COMPARE_TENDERS] ✓ Comparación completada: {len(tenders)} licitaciones")

        return {
            'success': True,
            'comparison': comparison
        }

    except Exception as e:
        logger.error(f"[COMPARE_TENDERS] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


TOOL_DEFINITION.function = compare_tenders
