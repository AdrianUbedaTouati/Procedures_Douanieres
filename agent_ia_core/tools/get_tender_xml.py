# -*- coding: utf-8 -*-
"""
Tool: get_tender_xml

Obtiene el archivo XML completo de una licitación para análisis detallado.
"""

from typing import Dict, Any
from .auxiliary.tools_base import ToolDefinition
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="get_tender_xml",
    description=(
        "Obtiene el archivo XML COMPLETO de una licitación específica. "
        "USA ESTA HERRAMIENTA cuando: "
        "(1) get_tender_details NO tiene la información de contacto que necesitas (email, teléfono, website, fax), "
        "(2) Necesitas información técnica muy específica del XML original, "
        "(3) El usuario pregunta por datos que no aparecen en los campos básicos. "
        "IMPORTANTE: Esta herramienta devuelve el XML completo (3000-5000 tokens). Úsala solo cuando get_tender_details no tenga la información."
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

def get_tender_xml(tender_id: str, db_session=None, **kwargs) -> Dict[str, Any]:
    """
    Obtiene el XML completo de una licitación.

    Args:
        tender_id: ID de la licitación (ojs_notice_id)
        db_session: Sesión de base de datos Django (opcional)
        **kwargs: Argumentos adicionales

    Returns:
        Dict con el XML completo y metadata
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
        from django.db.models import Q

        logger.info(f"[GET_TENDER_XML] Buscando licitación: '{tender_id}'")

        tender = None

        # 1. Intento de búsqueda exacta
        try:
            tender = Tender.objects.get(ojs_notice_id=tender_id)
            logger.info(f"[GET_TENDER_XML] ✓ Búsqueda exacta exitosa")
        except Tender.DoesNotExist:
            logger.info(f"[GET_TENDER_XML] ✗ Búsqueda exacta falló, intentando flexible...")

            # 2. Búsqueda flexible
            matches = Tender.objects.filter(ojs_notice_id__icontains=tender_id)

            if matches.count() == 1:
                tender = matches.first()
                logger.info(f"[GET_TENDER_XML] ✓ Búsqueda flexible: {tender.ojs_notice_id}")
            elif matches.count() > 1:
                match_ids = [t.ojs_notice_id for t in matches[:5]]
                return {
                    'success': False,
                    'error': f'Múltiples licitaciones coinciden con "{tender_id}". Especifica el ID completo: {", ".join(match_ids[:5])}'
                }
            else:
                return {
                    'success': False,
                    'error': f'Licitación "{tender_id}" no encontrada. Verifica el ID (formato: XXXXXXXX-YYYY).'
                }

        # 3. Intentar leer desde archivo (source_path)
        xml_content = None
        if tender.source_path:
            import os
            if os.path.exists(tender.source_path):
                logger.info(f"[GET_TENDER_XML] ✓ Leyendo XML desde archivo: {tender.source_path}")
                with open(tender.source_path, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
            else:
                logger.warning(f"[GET_TENDER_XML] ✗ Archivo no existe: {tender.source_path}")

        # 4. Fallback: intentar leer desde xml_content en BD
        if not xml_content and tender.xml_content:
            logger.info(f"[GET_TENDER_XML] ✓ Usando xml_content de la base de datos")
            xml_content = tender.xml_content

        # 5. Si aún no hay XML, error
        if not xml_content:
            logger.error(f"[GET_TENDER_XML] ✗ Sin XML disponible para: {tender.ojs_notice_id}")
            return {
                'success': False,
                'error': f'Licitación {tender.ojs_notice_id} no tiene XML disponible (ni en archivo ni en BD).'
            }

        logger.info(f"[GET_TENDER_XML] ✓ XML recuperado: {len(xml_content)} caracteres")

        return {
            'success': True,
            'tender_id': tender.ojs_notice_id,
            'xml_content': xml_content,
            'xml_length': len(xml_content),
            'source_path': tender.source_path,
            'message': f'XML completo recuperado ({len(xml_content)} caracteres).'
        }

    except Exception as e:
        logger.error(f"[GET_TENDER_XML] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


TOOL_DEFINITION.function = get_tender_xml
