# -*- coding: utf-8 -*-
"""
Tool: get_tender_details

Obtiene información completa y detallada de una licitación específica por su ID.
"""

from typing import Dict, Any
from .base import ToolDefinition
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="get_tender_details",
    description=(
        "Obtiene información completa de una licitación específica (contacto, procedimiento, fechas, presupuesto, etc.) "
        "cuando conoces su ID exacto (formato: XXXXXXXX-YYYY). "
        "Usa esta herramienta cuando el usuario pregunte por detalles de una licitación concreta, información de contacto, "
        "cómo inscribirse, o fechas límite."
    ),
    parameters={
        "type": "object",
        "properties": {
            "tender_id": {
                "type": "string",
                "description": 'El ID de la licitación. Ejemplo: "00668461-2025"'
            }
        },
        "required": ["tender_id"]
    },
    function=None,
    category="detail"
)


# ============================================================================
# IMPLEMENTACIÓN
# ============================================================================

def get_tender_details(tender_id: str, db_session=None, **kwargs) -> Dict[str, Any]:
    """
    Obtiene detalles completos de una licitación específica.

    Args:
        tender_id: ID de la licitación (ej: "00668461-2025")
        db_session: Sesión de base de datos Django (opcional)
        **kwargs: Argumentos adicionales

    Returns:
        Dict con todos los detalles de la licitación
    """
    try:
        # Importar aquí para evitar circular imports
        import sys
        from pathlib import Path
        import django

        # Setup Django si no está configurado
        if not django.apps.apps.ready:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            import os
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
            django.setup()

        from apps.tenders.models import Tender
        from django.db.models import Q

        logger.info(f"[GET_TENDER_DETAILS] Buscando licitación: '{tender_id}'")

        tender = None

        # 1. Intento de búsqueda exacta
        try:
            tender = Tender.objects.get(ojs_notice_id=tender_id)
            logger.info(f"[GET_TENDER_DETAILS] ✓ Búsqueda exacta exitosa")
        except Tender.DoesNotExist:
            logger.info(f"[GET_TENDER_DETAILS] ✗ Búsqueda exacta falló, intentando flexible...")

            # 2. Búsqueda flexible
            normalized_id = tender_id
            if '-' in tender_id:
                parts = tender_id.split('-')
                normalized_id = parts[0].lstrip('0') + '-' + parts[1]

            matches = Tender.objects.filter(
                Q(ojs_notice_id__icontains=tender_id) |
                Q(ojs_notice_id__in=[normalized_id]) |
                Q(ojs_notice_id__icontains=normalized_id)
            ).distinct()

            if matches.count() == 1:
                tender = matches.first()
                logger.info(f"[GET_TENDER_DETAILS] ✓ Búsqueda flexible: {tender.ojs_notice_id}")
            elif matches.count() > 1:
                match_ids = [t.ojs_notice_id for t in matches[:5]]
                return {
                    'success': False,
                    'error': f'Múltiples licitaciones coinciden con "{tender_id}". Por favor, especifica el ID completo: {", ".join(match_ids[:5])}'
                }
            else:
                return {
                    'success': False,
                    'error': f'Licitación "{tender_id}" no encontrada. Verifica que el ID esté correcto (formato: XXXXXXXX-YYYY).'
                }

        # Construir respuesta con TODOS los detalles
        details = {
            'id': tender.ojs_notice_id,
            'title': tender.title,
            'description': tender.description,
            'short_description': tender.short_description,
            'buyer_name': tender.buyer_name,
            'buyer_type': tender.buyer_type,
        }

        # Datos financieros
        if tender.budget_amount:
            details['budget'] = {
                'amount': float(tender.budget_amount),
                'currency': tender.currency
            }

        # Clasificación
        if tender.cpv_codes:
            details['cpv_codes'] = tender.cpv_codes
        if tender.nuts_regions:
            details['nuts_regions'] = tender.nuts_regions
        if tender.contract_type:
            details['contract_type'] = tender.contract_type

        # Fechas
        if tender.publication_date:
            details['publication_date'] = tender.publication_date.isoformat()
        if tender.deadline:
            details['deadline'] = tender.deadline.isoformat()
        if tender.tender_deadline_date:
            details['tender_deadline_date'] = tender.tender_deadline_date.isoformat()
        if tender.tender_deadline_time:
            details['tender_deadline_time'] = tender.tender_deadline_time.isoformat()

        # Procedimiento
        if tender.procedure_type:
            details['procedure_type'] = tender.procedure_type
        if tender.award_criteria:
            details['award_criteria'] = tender.award_criteria

        # Contacto
        contact_info = {}
        if tender.contact_email:
            contact_info['email'] = tender.contact_email
        if tender.contact_phone:
            contact_info['phone'] = tender.contact_phone
        if tender.contact_url:
            contact_info['url'] = tender.contact_url
        if tender.contact_fax:
            contact_info['fax'] = tender.contact_fax
        if contact_info:
            details['contact'] = contact_info

        # TED URL
        details['ted_url'] = f"https://ted.europa.eu/udl?uri=TED:NOTICE:{tender.ojs_notice_id}:DATA:ES:HTML"

        logger.info(f"[GET_TENDER_DETAILS] ✓ Detalles obtenidos: {tender.ojs_notice_id}")

        return {
            'success': True,
            'tender': details
        }

    except Exception as e:
        logger.error(f"[GET_TENDER_DETAILS] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


TOOL_DEFINITION.function = get_tender_details
