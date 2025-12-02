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
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
                django.setup()

            from apps.tenders.models import Tender

            # Buscar la licitación con búsqueda flexible
            logger.info(f"[GET_TENDER_DETAILS] Buscando licitación con ID: '{tender_id}'")

            tender = None

            # 1. Intento de búsqueda exacta
            try:
                tender = Tender.objects.get(ojs_notice_id=tender_id)
                logger.info(f"[GET_TENDER_DETAILS] ✓ Búsqueda exacta exitosa: {tender.title}")
            except Tender.DoesNotExist:
                logger.info(f"[GET_TENDER_DETAILS] ✗ Búsqueda exacta falló, intentando búsqueda flexible...")

                # 2. Búsqueda flexible con múltiples estrategias
                from django.db.models import Q

                # Normalizar el ID de búsqueda (quitar ceros a la izquierda de la parte numérica)
                normalized_id = tender_id
                if '-' in tender_id:
                    parts = tender_id.split('-')
                    # Quitar ceros a la izquierda de la primera parte (número)
                    normalized_id = parts[0].lstrip('0') + '-' + parts[1]
                    logger.info(f"[GET_TENDER_DETAILS] ID normalizado: '{tender_id}' -> '{normalized_id}'")

                # Buscar con múltiples estrategias:
                # - ID original contiene el ID de DB (ej: "00690603-2025" contiene "690603-2025")
                # - ID de DB contiene el ID original
                # - ID normalizado es exacto
                # - ID normalizado está contenido
                matches = Tender.objects.filter(
                    Q(ojs_notice_id__icontains=tender_id) |
                    Q(ojs_notice_id__in=[normalized_id]) |
                    Q(ojs_notice_id__icontains=normalized_id)
                ).distinct()

                # Si no hay matches con contains, intentar buscar IDs de DB que estén contenidos en el ID de búsqueda
                if matches.count() == 0:
                    logger.info(f"[GET_TENDER_DETAILS] Intentando búsqueda inversa (DB ID dentro de búsqueda)...")
                    all_tenders = Tender.objects.all()
                    for t in all_tenders:
                        # Verificar si el ID de DB está contenido en el ID de búsqueda
                        if t.ojs_notice_id in tender_id or t.ojs_notice_id in normalized_id:
                            matches = Tender.objects.filter(ojs_notice_id=t.ojs_notice_id)
                            break

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
                    # Sin coincidencias, sugerir IDs similares
                    logger.warning(f"[GET_TENDER_DETAILS] ✗ Sin coincidencias para: {tender_id}")

                    # Buscar IDs similares para ayudar al usuario
                    similar_ids = []
                    if '-' in tender_id:
                        year_part = tender_id.split('-')[1]
                        similar = Tender.objects.filter(ojs_notice_id__endswith=f'-{year_part}')[:5]
                        similar_ids = [t.ojs_notice_id for t in similar]

                    error_msg = f'Licitación "{tender_id}" no encontrada.'
                    if similar_ids:
                        error_msg += f' IDs disponibles del mismo año: {", ".join(similar_ids)}'
                    else:
                        error_msg += ' Verifica que el ID esté correcto (formato: XXXXXXXX-YYYY).'

                    return {
                        'success': False,
                        'error': error_msg
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

            # Metadata
            if tender.source_path:
                details['source_path'] = tender.source_path
            if tender.indexed_at:
                details['indexed_at'] = tender.indexed_at.isoformat()

            # TED URL (generada desde ojs_notice_id)
            details['ted_url'] = f"https://ted.europa.eu/udl?uri=TED:NOTICE:{tender.ojs_notice_id}:DATA:ES:HTML"

            # Campos adicionales desde parsed_summary
            if tender.parsed_summary:
                optional = tender.parsed_summary.get('OPTIONAL', {})
                required = tender.parsed_summary.get('REQUIRED', {})

                # CPV principal completo (desde REQUIRED)
                if required.get('cpv_main'):
                    details['cpv_main'] = required['cpv_main']

                # Requisitos de elegibilidad
                if optional.get('eligibility_requirements'):
                    details['eligibility_requirements'] = optional['eligibility_requirements']

                # Referencias externas (URLs a portales oficiales)
                if optional.get('external_references'):
                    details['external_references'] = optional['external_references']

                # Documentos adjuntos
                if optional.get('attachments'):
                    details['attachments'] = optional['attachments']

                # Lotes del contrato
                if optional.get('lots'):
                    details['lots'] = optional['lots']

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
    description = """Obtiene el archivo XML COMPLETO de una licitación específica.

USA ESTA HERRAMIENTA cuando:
- get_tender_details NO tiene la información de contacto que necesitas (email, teléfono, website, fax)
- Necesitas información técnica muy específica del XML original
- El usuario pregunta por datos que no aparecen en los campos básicos

IMPORTANTE: Esta herramienta devuelve el XML completo (3000-5000 tokens). Úsala solo cuando get_tender_details no tenga la información."""

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
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
                django.setup()

            from apps.tenders.models import Tender

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
                'tender_id': tender.ojs_notice_id,
                'xml_content': xml_content,  # XML completo sin límite
                'xml_length': len(xml_content),
                'source_path': tender.source_path,
                'message': f'XML completo recuperado ({len(xml_content)} caracteres).'
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
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
                django.setup()

            from apps.tenders.models import Tender

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
