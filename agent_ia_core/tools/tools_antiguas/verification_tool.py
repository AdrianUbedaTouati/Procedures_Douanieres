# -*- coding: utf-8 -*-
"""
Tool para verificar campos críticos con XML original (Verification).
Portado desde EFormsRAGAgent._verify_node().

Esta tool permite validar campos críticos (presupuesto, deadline, criterios)
consultando directamente el XML original con XPath, garantizando exactitud.
"""

from typing import List, Dict, Any
from .base import BaseTool
import logging

logger = logging.getLogger(__name__)


class VerifyFieldsTool(BaseTool):
    """
    Verifica campos críticos directamente del XML original.

    Esta tool usa XPath para extraer valores exactos de:
    - Presupuesto (budget_eur)
    - Fecha límite (tender_deadline_date, tender_deadline_time)
    - Criterios de adjudicación (award_criteria con pesos)

    Garantiza exactitud al consultar el XML original en lugar de
    confiar en valores extraídos/vectorizados que pueden tener errores.

    Casos de uso:
    - Cuando necesitas el presupuesto EXACTO de una licitación
    - Cuando el deadline es crítico para la decisión
    - Para validar información antes de responder al usuario
    - Cuando el usuario pregunta por valores específicos (no rangos)

    Impacto en rendimiento:
    - NO añade llamadas al LLM (operaciones locales)
    - Parseo de XML: ~100-200ms primera vez
    - Subsecuentes: ~10-20ms (caching)
    - Impacto mínimo comparado con grading

    Ejemplo de uso:
        Usuario: "¿Cuál es el presupuesto EXACTO de la licitación 668461-2025?"
        1. search_tenders → encontrar 668461-2025
        2. verify_fields(tender_id='668461-2025', fields=['budget'])
        3. Responder con valor verificado: "961,200.00 EUR (✓ verificado en XML)"
    """

    def __init__(self):
        """
        Inicializa la tool con XmlLookupTool para validación.
        """
        from agent_ia_core.parser.tools_xml import XmlLookupTool
        self.xml_lookup = XmlLookupTool()
        self.name = "verify_fields"
        self.description = (
            "Verifica campos críticos (presupuesto, deadline, criterios de adjudicación) "
            "directamente del XML original usando XPath. "
            "Úsala cuando necesites valores EXACTOS y confiables, no aproximados."
        )

    def get_schema(self) -> Dict[str, Any]:
        """Retorna el schema OpenAI Function Calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "tender_id": {
                        "type": "string",
                        "description": "ID de la licitación a verificar (ojs_notice_id, ej: '668461-2025')"
                    },
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["budget", "deadline", "award_criteria"]
                        },
                        "description": "Campos a verificar: 'budget' (presupuesto), 'deadline' (fecha límite), 'award_criteria' (criterios con pesos)"
                    }
                },
                "required": ["tender_id", "fields"]
            }
        }

    def run(self, tender_id: str, fields: List[str]) -> Dict[str, Any]:
        """
        Verifica campos críticos del XML original.

        Para cada campo solicitado, ejecuta XPath en el XML original
        para extraer el valor exacto.

        Args:
            tender_id: ID de la licitación (ojs_notice_id)
            fields: Lista de campos a verificar ['budget', 'deadline', 'award_criteria']

        Returns:
            Dict con:
                - success: bool - Si la operación fue exitosa
                - tender_id: str - ID de la licitación
                - verified_fields: List[Dict] - Valores verificados con metadata
                - verification_source: str - 'XML original'
                - error: str - Mensaje de error (si falla)
        """
        try:
            from apps.tenders.models import Tender

            logger.info(f"[VERIFICATION] Verificando {fields} para tender {tender_id}")

            # Obtener tender desde la BD
            tender = Tender.objects.filter(ojs_notice_id=tender_id).first()
            if not tender:
                error_msg = f"Tender {tender_id} no encontrado en la base de datos"
                logger.error(f"[VERIFICATION] {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'tender_id': tender_id
                }

            if not tender.source_path:
                error_msg = f"Tender {tender_id} no tiene XML disponible"
                logger.warning(f"[VERIFICATION] {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'tender_id': tender_id,
                    'message': "XML no disponible. Usando valores de la base de datos como fallback."
                }

            verified_fields = []

            # Verificar presupuesto
            if "budget" in fields:
                logger.debug(f"[VERIFICATION] Verificando presupuesto...")
                budget_info = self.xml_lookup.lookup_budget(tender.source_path)
                if budget_info:
                    verified_fields.append({
                        "field": "budget",
                        "value": budget_info['budget_eur'],
                        "currency": budget_info['currency'],
                        "xpath": budget_info['xpath'],
                        "formatted": f"{budget_info['budget_eur']:,.2f} {budget_info['currency']}",
                        "verified": True
                    })
                    logger.info(f"[VERIFICATION] ✓ Budget: {budget_info['budget_eur']:,.2f} {budget_info['currency']}")
                else:
                    logger.warning(f"[VERIFICATION] ✗ Budget no encontrado en XML")
                    verified_fields.append({
                        "field": "budget",
                        "verified": False,
                        "message": "Presupuesto no encontrado en el XML"
                    })

            # Verificar deadline
            if "deadline" in fields:
                logger.debug(f"[VERIFICATION] Verificando deadline...")
                deadline_info = self.xml_lookup.lookup_deadline(tender.source_path)
                if deadline_info:
                    time_part = deadline_info.get('tender_deadline_time', '')
                    verified_fields.append({
                        "field": "deadline",
                        "date": deadline_info['tender_deadline_date'],
                        "time": time_part,
                        "xpath_date": deadline_info['xpath_date'],
                        "xpath_time": deadline_info.get('xpath_time'),
                        "formatted": f"{deadline_info['tender_deadline_date']}" + (f" {time_part}" if time_part else ""),
                        "verified": True
                    })
                    logger.info(f"[VERIFICATION] ✓ Deadline: {deadline_info['tender_deadline_date']} {time_part}")
                else:
                    logger.warning(f"[VERIFICATION] ✗ Deadline no encontrado en XML")
                    verified_fields.append({
                        "field": "deadline",
                        "verified": False,
                        "message": "Fecha límite no encontrada en el XML"
                    })

            # Verificar criterios de adjudicación
            if "award_criteria" in fields:
                logger.debug(f"[VERIFICATION] Verificando criterios de adjudicación...")
                criteria_info = self.xml_lookup.lookup_award_criteria(tender.source_path)
                if criteria_info:
                    # Formatear criterios para mostrar
                    criteria_formatted = []
                    for c in criteria_info:
                        weight = c.get('weight', 'N/A')
                        criteria_formatted.append(f"{c['name']} ({weight}%)" if weight != 'N/A' else c['name'])

                    verified_fields.append({
                        "field": "award_criteria",
                        "criteria": criteria_info,
                        "count": len(criteria_info),
                        "formatted": ", ".join(criteria_formatted),
                        "verified": True
                    })
                    logger.info(f"[VERIFICATION] ✓ Award criteria: {len(criteria_info)} criterios encontrados")
                else:
                    logger.warning(f"[VERIFICATION] ✗ Award criteria no encontrados en XML")
                    verified_fields.append({
                        "field": "award_criteria",
                        "verified": False,
                        "message": "Criterios de adjudicación no encontrados en el XML"
                    })

            verified_count = sum(1 for f in verified_fields if f.get('verified', False))
            logger.info(f"[VERIFICATION] Completado: {verified_count}/{len(fields)} campos verificados exitosamente")

            return {
                'success': True,
                'tender_id': tender_id,
                'verified_fields': verified_fields,
                'verification_source': 'XML original',
                'verified_count': verified_count,
                'total_requested': len(fields),
                'message': f"Verificados {verified_count}/{len(fields)} campos del XML original."
            }

        except Exception as e:
            logger.error(f"[VERIFICATION] Error al verificar campos: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'tender_id': tender_id,
                'message': f"Error en verificación: {str(e)}"
            }
