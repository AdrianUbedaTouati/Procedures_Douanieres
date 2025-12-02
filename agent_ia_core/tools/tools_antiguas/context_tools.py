# -*- coding: utf-8 -*-
"""
Tools para obtener información de contexto del usuario:
- Información de la empresa del usuario
- Resumen de licitaciones disponibles
"""

from typing import Dict, Any
import logging
from .base import BaseTool

logger = logging.getLogger(__name__)


class GetCompanyInfoTool(BaseTool):
    """
    Tool para obtener la información de la empresa del usuario.

    Esta herramienta permite al agente consultar el perfil de empresa del usuario
    cuando necesite información personalizada para recomendaciones o respuestas.
    """

    name = "get_company_info"
    description = (
        "Obtiene información sobre la empresa y perfil del usuario. "
        "**IMPORTANTE: USA ESTA TOOL SIEMPRE que el usuario pida recomendaciones personalizadas o preguntas abiertas** "
        "(ej: 'dame la mejor licitación para mí', 'qué licitación me interesa', 'cuál me conviene'). "
        "Usa esta herramienta cuando el usuario pregunte sobre su empresa, "
        "o cuando necesites información del perfil de empresa para dar recomendaciones personalizadas. "
        "Devuelve: nombre, sector, empleados, CPV codes, regiones NUTS, capacidades, certificaciones, presupuesto. "
        "Con esta información puedes hacer análisis de fit y justificar recomendaciones con datos objetivos."
    )

    def __init__(self, user):
        """
        Inicializa la tool con el usuario.

        Args:
            user: Instancia del modelo User de Django
        """
        super().__init__()
        self.user = user

    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta la consulta de información de empresa.

        Returns:
            Dict con:
                - success: bool
                - data: información de la empresa formateada
                - error: mensaje de error si falla
        """
        try:
            from apps.company.models import CompanyProfile

            # Buscar perfil de empresa
            profile = CompanyProfile.objects.filter(user=self.user).first()

            if not profile:
                return {
                    'success': False,
                    'data': None,
                    'error': 'El usuario no tiene un perfil de empresa configurado.'
                }

            # Obtener contexto usando el método del modelo
            company_context = profile.get_chat_context()

            # También devolver datos estructurados para procesamiento
            company_data = {
                'company_name': profile.company_name,
                'company_description': profile.company_description_text,
                'sectors': profile.sectors[:5] if profile.sectors else [],
                'employees': profile.employees,
                'cpv_codes': profile.preferred_cpv_codes[:10] if profile.preferred_cpv_codes else [],  # Primeros 10
                'nuts_regions': profile.preferred_nuts_regions[:10] if profile.preferred_nuts_regions else [],  # Primeras 10
                'budget_range': profile.budget_range if profile.budget_range else {},
            }

            return {
                'success': True,
                'data': {
                    'formatted_context': company_context,
                    'structured_data': company_data
                }
            }

        except Exception as e:
            logger.error(f"Error obteniendo información de empresa: {e}")
            return {
                'success': False,
                'data': None,
                'error': f'Error al obtener información de empresa: {str(e)}'
            }

    def get_schema(self) -> Dict[str, Any]:
        """
        Schema de la tool (sin parámetros, solo consulta).

        Returns:
            Dict con schema OpenAI Function Calling
        """
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {},  # No requiere parámetros
                'required': []
            }
        }


class GetTendersSummaryTool(BaseTool):
    """
    Tool para obtener un resumen de las licitaciones disponibles en la base de datos.

    Esta herramienta proporciona una vista general de las licitaciones más recientes
    almacenadas, útil para dar contexto al usuario sobre qué información está disponible.
    """

    name = "get_tenders_summary"
    description = (
        "Obtiene un resumen de las licitaciones públicas disponibles en la base de datos. "
        "Usa esta herramienta al inicio de una conversación para conocer qué licitaciones hay disponibles, "
        "o cuando el usuario pregunte sobre el estado general de las licitaciones. "
        "Devuelve: lista resumida de las últimas licitaciones con ID, título, organismo, presupuesto y fecha."
    )

    def __init__(self, user):
        """
        Inicializa la tool con el usuario.

        Args:
            user: Instancia del modelo User de Django
        """
        super().__init__()
        self.user = user

    def run(self, limit: int = None) -> Dict[str, Any]:
        """
        Ejecuta la consulta de resumen de licitaciones.

        Args:
            limit: Número máximo de licitaciones a incluir (default: None = todas)

        Returns:
            Dict con:
                - success: bool
                - data: resumen de licitaciones formateado
                - error: mensaje de error si falla
        """
        try:
            from apps.tenders.models import Tender
            import json

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

            return {
                'success': True,
                'data': {
                    'formatted_summary': formatted_summary,
                    'tenders_list': tenders_list,
                    'total_count': tenders.count()
                }
            }

        except Exception as e:
            logger.error(f"Error obteniendo resumen de licitaciones: {e}")
            return {
                'success': False,
                'data': None,
                'error': f'Error al obtener resumen de licitaciones: {str(e)}'
            }

    def get_schema(self) -> Dict[str, Any]:
        """
        Schema de la tool.

        Returns:
            Dict con schema OpenAI Function Calling
        """
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'limit': {
                        'type': 'integer',
                        'description': 'Número máximo de licitaciones a incluir en el resumen. Si no se especifica, devuelve TODAS las licitaciones disponibles.',
                        'minimum': 1
                    }
                },
                'required': []  # limit es opcional (None = todas)
            }
        }
