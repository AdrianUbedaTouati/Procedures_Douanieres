# -*- coding: utf-8 -*-
"""
Tool: web_search

Búsqueda web usando Google Custom Search API para encontrar información actualizada en internet.
"""

from typing import Dict, Any
from agent_ia_core.chatbots.shared import ToolDefinition
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="web_search",
    description=(
        "Busca información actualizada en internet. Retorna URLs y snippets breves. "
        "Para información detallada de las URLs encontradas, usa browse_webpage después."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Términos de búsqueda. Ejemplo: 'precio Bitcoin', 'Telefónica ingresos 2024'"
            },
            "limit": {
                "type": "integer",
                "description": "Número de resultados (1-10). Por defecto: 5",
                "minimum": 1,
                "maximum": 10,
                "default": 5
            }
        },
        "required": ["query"]
    },
    function=None,
    category="web"
)


# ============================================================================
# IMPLEMENTACIÓN
# ============================================================================

def web_search(query: str, limit: int = 5, api_key: str = None, engine_id: str = None, **kwargs) -> Dict[str, Any]:
    """
    Ejecuta una búsqueda web usando Google Custom Search API.

    Args:
        query: Término de búsqueda
        limit: Número máximo de resultados (1-10, default 5)
        api_key: Google Custom Search API Key (inyectado por registry)
        engine_id: Custom Search Engine ID (inyectado por registry)
        **kwargs: Argumentos adicionales

    Returns:
        Dict con formato:
        {
            'success': True/False,
            'data': {
                'query': str,
                'results': [
                    {
                        'title': str,
                        'snippet': str,
                        'url': str,
                        'displayUrl': str
                    },
                    ...
                ],
                'count': int
            },
            'error': str (si success=False)
        }
    """
    try:
        # Validar parámetros
        if not query or not query.strip():
            return {
                'success': False,
                'error': 'Query no puede estar vacía'
            }

        limit = max(1, min(limit, 10))  # Limitar entre 1 y 10

        # Validar credenciales
        if not api_key or not engine_id:
            return {
                'success': False,
                'error': 'Google Search API no configurada. Requiere api_key y engine_id en configuración de usuario.'
            }

        # Importar googleapiclient solo cuando se necesita
        try:
            from googleapiclient.discovery import build
        except ImportError:
            return {
                'success': False,
                'error': 'google-api-python-client no instalado. Ejecuta: pip install google-api-python-client'
            }

        logger.info(f"[WEB_SEARCH] Buscando: '{query}' (limit={limit})")

        # Crear servicio de búsqueda
        service = build("customsearch", "v1", developerKey=api_key)

        # Ejecutar búsqueda
        result = service.cse().list(
            q=query,
            cx=engine_id,
            num=limit
        ).execute()

        # Procesar resultados
        items = result.get('items', [])

        if not items:
            logger.info(f"[WEB_SEARCH] No se encontraron resultados para: '{query}'")
            return {
                'success': True,
                'data': {
                    'query': query,
                    'results': [],
                    'count': 0
                },
                'message': 'No se encontraron resultados. Intenta con otros términos de búsqueda.'
            }

        # Formatear resultados
        formatted_results = []
        for item in items:
            formatted_results.append({
                'title': item.get('title', 'Sin título'),
                'snippet': item.get('snippet', 'Sin descripción disponible'),
                'url': item.get('link', ''),
                'displayUrl': item.get('displayLink', '')
            })

        logger.info(f"[WEB_SEARCH] Encontrados {len(formatted_results)} resultados para: '{query}'")

        return {
            'success': True,
            'data': {
                'query': query,
                'results': formatted_results,
                'count': len(formatted_results)
            },
            'message': f'Se encontraron {len(formatted_results)} resultados. Usa browse_webpage con las URLs para obtener información detallada.'
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[WEB_SEARCH] Error: {error_msg}", exc_info=True)

        # Detectar errores específicos
        if 'quota' in error_msg.lower() or 'limit' in error_msg.lower():
            return {
                'success': False,
                'error': 'Cuota de Google Search API excedida. Has usado tus 100 búsquedas gratuitas diarias. Espera 24 horas o actualiza tu plan.'
            }
        elif 'invalid' in error_msg.lower() and 'key' in error_msg.lower():
            return {
                'success': False,
                'error': 'API key de Google Search inválida. Verifica las credenciales en configuración de perfil.'
            }
        elif 'invalid' in error_msg.lower() and ('cx' in error_msg.lower() or 'engine' in error_msg.lower()):
            return {
                'success': False,
                'error': 'ID de Custom Search Engine (cx) inválido. Verifica las credenciales en configuración de perfil.'
            }
        else:
            return {
                'success': False,
                'error': f'Error en búsqueda web: {error_msg}'
            }


TOOL_DEFINITION.function = web_search
