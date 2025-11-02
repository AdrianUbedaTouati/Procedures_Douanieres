# -*- coding: utf-8 -*-
"""
Tools para obtener información detallada de licitaciones.
"""

from typing import Dict, Any
from .base import BaseTool
import logging

logger = logging.getLogger(__name__)


class GetTenderDetailsTool(BaseTool):
    """
    Obtiene TODOS los detalles de una licitación específica.
    """

    name = "get_tender_details"
    description = "Obtiene información completa de una licitación específica (contacto, procedimiento, fechas, presupuesto, etc.) cuando conoces su ID exacto (formato: XXXXXXXX-YYYY). Usa esta herramienta cuando el usuario pregunte por detalles de una licitación concreta, información de contacto, cómo inscribirse, o fechas límite."

    def __init__(self, db_session=None):
        """
        Args:
            db_session: Sesión de base de datos Django (opcional)
        """
        super().__init__()
        self.db_session = db_session

    def run(self, tender_id: str) -> Dict[str, Any]:
        """
        Obtiene detalles completos de una licitación.

        Args:
            tender_id: ID de la licitación (ej: "00668461-2025")

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
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
                django.setup()

            from tenders.models import Tender

            # Buscar la licitación con búsqueda flexible
            logger.info(f"[GET_TENDER_DETAILS] Buscando licitación con ID: '{tender_id}'")

            tender = None

            # 1. Intento de búsqueda exacta
            try:
                tender = Tender.objects.get(ojs_notice_id=tender_id)
                logger.info(f"[GET_TENDER_DETAILS] ✓ Búsqueda exacta exitosa: {tender.title}")
            except Tender.DoesNotExist:
                logger.info(f"[GET_TENDER_DETAILS] ✗ Búsqueda exacta falló, intentando búsqueda flexible...")

                # 2. Búsqueda flexible: IDs que contienen el string proporcionado
                matches = Tender.objects.filter(ojs_notice_id__icontains=tender_id)

                if matches.count() == 1:
                    # Solo una coincidencia, usar esa
                    tender = matches.first()
                    logger.info(f"[GET_TENDER_DETAILS] ✓ Búsqueda flexible encontró 1 match: {tender.ojs_notice_id}")
                elif matches.count() > 1:
                    # Múltiples coincidencias, pedir clarificación
                    match_ids = [t.ojs_notice_id for t in matches[:5]]
                    logger.warning(f"[GET_TENDER_DETAILS] ✗ Múltiples coincidencias ({matches.count()}): {match_ids}")
                    return {
                        'success': False,
                        'error': f'Múltiples licitaciones coinciden con "{tender_id}". Por favor, especifica el ID completo: {", ".join(match_ids[:5])}'
                    }
                else:
                    # Sin coincidencias
                    logger.warning(f"[GET_TENDER_DETAILS] ✗ Sin coincidencias para: {tender_id}")
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
            if contact_info:
                details['contact'] = contact_info

            # Metadata
            if tender.source_path:
                details['source_path'] = tender.source_path
            if tender.indexed_at:
                details['indexed_at'] = tender.indexed_at.isoformat()

            return {
                'success': True,
                'tender': details
            }

        except Exception as e:
            logger.error(f"Error en get_tender_details: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_schema(self) -> Dict[str, Any]:
        """Schema de la tool."""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'tender_id': {
                        'type': 'string',
                        'description': 'El ID de la licitación. Ejemplo: "00668461-2025"'
                    }
                },
                'required': ['tender_id']
            }
        }


class GetTenderXMLTool(BaseTool):
    """
    Obtiene el XML completo de una licitación para análisis detallado.
    """

    name = "get_tender_xml"
    description = "Obtiene el archivo XML completo de una licitación específica. Usa esta función cuando el usuario necesite ver el XML original, analizar estructura técnica detallada, o extraer información muy específica que no está en los campos básicos."

    def __init__(self, db_session=None):
        """
        Args:
            db_session: Sesión de base de datos Django (opcional)
        """
        super().__init__()
        self.db_session = db_session

    def run(self, tender_id: str) -> Dict[str, Any]:
        """
        Obtiene el XML completo de una licitación.

        Args:
            tender_id: ID de la licitación (ojs_notice_id)

        Returns:
            Dict con el XML completo y metadata
        """
        try:
            # Setup Django si es necesario
            import django
            if not django.apps.apps.ready:
                import os
                import sys
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
                django.setup()

            from tenders.models import Tender

            # Buscar la licitación con búsqueda flexible
            logger.info(f"[GET_TENDER_XML] Buscando licitación con ID: '{tender_id}'")

            tender = None

            # 1. Intento de búsqueda exacta
            try:
                tender = Tender.objects.get(ojs_notice_id=tender_id)
                logger.info(f"[GET_TENDER_XML] ✓ Búsqueda exacta exitosa: {tender.ojs_notice_id}")
            except Tender.DoesNotExist:
                logger.info(f"[GET_TENDER_XML] ✗ Búsqueda exacta falló, intentando búsqueda flexible...")

                # 2. Búsqueda flexible
                matches = Tender.objects.filter(ojs_notice_id__icontains=tender_id)

                if matches.count() == 1:
                    tender = matches.first()
                    logger.info(f"[GET_TENDER_XML] ✓ Búsqueda flexible encontró 1 match: {tender.ojs_notice_id}")
                elif matches.count() > 1:
                    match_ids = [t.ojs_notice_id for t in matches[:5]]
                    logger.warning(f"[GET_TENDER_XML] ✗ Múltiples coincidencias ({matches.count()}): {match_ids}")
                    return {
                        'success': False,
                        'error': f'Múltiples licitaciones coinciden con "{tender_id}". Especifica el ID completo: {", ".join(match_ids[:5])}'
                    }
                else:
                    logger.warning(f"[GET_TENDER_XML] ✗ Sin coincidencias para: {tender_id}")
                    return {
                        'success': False,
                        'error': f'Licitación "{tender_id}" no encontrada. Verifica el ID (formato: XXXXXXXX-YYYY).'
                    }

            # Leer el XML del archivo o base de datos
            xml_content = None

            # 3. Intentar leer desde archivo (source_path)
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

            return {
                'success': True,
                'tender_id': tender_id,
                'xml_content': xml_content[:5000],  # Limitar a 5000 chars para no sobrecargar
                'xml_length': len(xml_content),
                'source_path': tender.source_path,
                'message': f'XML recuperado ({len(xml_content)} caracteres). Mostrando primeros 5000 caracteres.'
            }

        except Exception as e:
            logger.error(f"Error en get_tender_xml: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_schema(self) -> Dict[str, Any]:
        """Retorna el schema de la tool en formato OpenAI Function Calling."""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'tender_id': {
                        'type': 'string',
                        'description': 'El ID de la licitación. Ejemplo: "00668461-2025"'
                    }
                },
                'required': ['tender_id']
            }
        }


class CompareTendersTool(BaseTool):
    """
    Compara múltiples licitaciones lado a lado para análisis.
    """

    name = "compare_tenders"
    description = "Compara dos o más licitaciones mostrando diferencias y similitudes. Usa esta función cuando el usuario quiera comparar licitaciones, ver cuál es mejor, o analizar diferencias entre opciones. Requiere al menos 2 IDs de licitaciones."

    def __init__(self, db_session=None):
        super().__init__()
        self.db_session = db_session

    def run(self, tender_ids: list) -> Dict[str, Any]:
        try:
            if not tender_ids or len(tender_ids) < 2:
                return {'success': False, 'error': 'Se requieren al menos 2 IDs para comparar'}

            import django
            if not django.apps.apps.ready:
                import os, sys
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
                django.setup()

            from tenders.models import Tender

            tenders = []
            for tender_id in tender_ids[:5]:
                try:
                    tender = Tender.objects.get(ojs_notice_id=tender_id)
                    tenders.append(tender)
                except Tender.DoesNotExist:
                    return {'success': False, 'error': f'Licitación {tender_id} no encontrada'}

            comparison = {'count': len(tenders), 'tenders': [], 'summary': {}}
            budgets, deadlines = [], []

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
                if tender.budget_amount:
                    budgets.append(float(tender.budget_amount))
                if tender.tender_deadline_date:
                    deadlines.append(tender.tender_deadline_date)
                comparison['tenders'].append(tender_data)

            if budgets:
                comparison['summary']['budget_comparison'] = {
                    'min': min(budgets), 'max': max(budgets),
                    'avg': sum(budgets)/len(budgets),
                    'difference': max(budgets)-min(budgets)
                }

            return {'success': True, 'comparison': comparison}
        except Exception as e:
            logger.error(f"Error en compare_tenders: {e}")
            return {'success': False, 'error': str(e)}

    def get_schema(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'tender_ids': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Lista de IDs a comparar. Ejemplo: ["12345-2025", "67890-2025"]. Mínimo 2, máximo 5',
                        'minItems': 2,
                        'maxItems': 5
                    }
                },
                'required': ['tender_ids']
            }
        }
