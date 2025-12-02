# -*- coding: utf-8 -*-
"""
Tool: get_company_info

Obtiene información sobre la empresa y perfil del usuario para recomendaciones personalizadas.
"""

from typing import Dict, Any
from .base import ToolDefinition
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="get_company_info",
    description=(
        "Obtiene información sobre la empresa y perfil del usuario. "
        "**IMPORTANTE: USA ESTA TOOL SIEMPRE que el usuario pida recomendaciones personalizadas o preguntas abiertas** "
        "(ej: 'dame la mejor licitación para mí', 'qué licitación me interesa', 'cuál me conviene'). "
        "Usa esta herramienta cuando el usuario pregunte sobre su empresa, "
        "o cuando necesites información del perfil de empresa para dar recomendaciones personalizadas. "
        "Devuelve: nombre, sector, empleados, CPV codes, regiones NUTS, capacidades, certificaciones, presupuesto. "
        "Con esta información puedes hacer análisis de fit y justificar recomendaciones con datos objetivos."
    ),
    parameters={
        "type": "object",
        "properties": {},  # No requiere parámetros
        "required": []
    },
    function=None,
    category="context"
)


# ============================================================================
# IMPLEMENTACIÓN
# ============================================================================

def get_company_info(user=None, **kwargs) -> Dict[str, Any]:
    """
    Obtiene información de la empresa del usuario.

    Args:
        user: Instancia del modelo User de Django
        **kwargs: Argumentos adicionales

    Returns:
        Dict con información de la empresa formateada
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

        from apps.company.models import CompanyProfile

        logger.info(f"[GET_COMPANY_INFO] Obteniendo perfil de usuario: {user}")

        # Buscar perfil de empresa
        profile = CompanyProfile.objects.filter(user=user).first()

        if not profile:
            logger.warning(f"[GET_COMPANY_INFO] Usuario sin perfil de empresa")
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
            'cpv_codes': profile.preferred_cpv_codes[:10] if profile.preferred_cpv_codes else [],
            'nuts_regions': profile.preferred_nuts_regions[:10] if profile.preferred_nuts_regions else [],
            'budget_range': profile.budget_range if profile.budget_range else {},
        }

        logger.info(f"[GET_COMPANY_INFO] ✓ Perfil obtenido: {company_data['company_name']}")

        return {
            'success': True,
            'data': {
                'formatted_context': company_context,
                'structured_data': company_data
            }
        }

    except Exception as e:
        logger.error(f"[GET_COMPANY_INFO] Error: {e}", exc_info=True)
        return {
            'success': False,
            'data': None,
            'error': f'Error al obtener información de empresa: {str(e)}'
        }


TOOL_DEFINITION.function = get_company_info
