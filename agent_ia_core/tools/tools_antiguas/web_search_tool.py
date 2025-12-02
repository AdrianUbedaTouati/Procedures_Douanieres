# -*- coding: utf-8 -*-
"""
Tool para búsqueda web usando Google Custom Search API.
Permite al agente buscar información actualizada en internet.
"""

from typing import Dict, Any, List
import logging
from .base import BaseTool

logger = logging.getLogger(__name__)


class GoogleWebSearchTool(BaseTool):
    """
    Tool para realizar búsquedas web usando Google Custom Search API.

    Permite al agente buscar información actualizada en internet cuando
    la información de la base de datos de licitaciones no es suficiente.
    """

    name = "web_search"
    description = """Search the web for up-to-date real-time information using Google Custom Search API.

Use this tool to find current information about ANY topic, including:
- Current prices, exchange rates, stock values (e.g., Bitcoin price, EUR/USD rate)
- Recent news and events (e.g., latest developments, breaking news)
- Company information and updates
- Technical specifications and product details
- Regulations, laws, and legal frameworks
- Statistics and data
- ANY other topic that requires real-time or recent information

IMPORTANT: This tool can search for ANY topic, not just procurement or tenders.
Use it whenever you need information that is current, recent, or not in the tender database.

Input: A search query string and optional limit for number of results.
Output: List of search results with titles, snippets, and URLs."""

    def __init__(self, api_key: str, engine_id: str):
        """
        Inicializa la tool con credenciales de Google Search API.

        Args:
            api_key: Google Custom Search API Key
            engine_id: Custom Search Engine ID (cx parameter)
        """
        self.api_key = api_key
        self.engine_id = engine_id
        super().__init__()

    def run(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Ejecuta una búsqueda web usando Google Custom Search API.

        Args:
            query: Término de búsqueda
            limit: Número máximo de resultados (1-10, default 5)

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
                    'error': 'Query cannot be empty'
                }

            limit = max(1, min(limit, 10))  # Limitar entre 1 y 10

            # Importar googleapiclient solo cuando se necesita
            try:
                from googleapiclient.discovery import build
            except ImportError:
                return {
                    'success': False,
                    'error': 'google-api-python-client not installed. Run: pip install google-api-python-client'
                }

            logger.info(f"[WEB_SEARCH] Buscando: '{query}' (limit={limit})")

            # Crear servicio de búsqueda
            service = build("customsearch", "v1", developerKey=self.api_key)

            # Ejecutar búsqueda
            result = service.cse().list(
                q=query,
                cx=self.engine_id,
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
                    'message': 'No results found'
                }

            # Formatear resultados
            formatted_results = []
            for item in items:
                formatted_results.append({
                    'title': item.get('title', 'No title'),
                    'snippet': item.get('snippet', 'No description available'),
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
                }
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[WEB_SEARCH] Error: {error_msg}", exc_info=True)

            # Detectar errores específicos
            if 'quota' in error_msg.lower() or 'limit' in error_msg.lower():
                return {
                    'success': False,
                    'error': 'Google Search API quota exceeded. You have used your free 100 searches/day. Wait 24 hours or upgrade your plan.'
                }
            elif 'invalid' in error_msg.lower() and 'key' in error_msg.lower():
                return {
                    'success': False,
                    'error': 'Invalid Google Search API key. Please check your credentials in profile settings.'
                }
            elif 'invalid' in error_msg.lower() and ('cx' in error_msg.lower() or 'engine' in error_msg.lower()):
                return {
                    'success': False,
                    'error': 'Invalid Custom Search Engine ID (cx). Please check your credentials in profile settings.'
                }
            else:
                return {
                    'success': False,
                    'error': f'Web search error: {error_msg}'
                }

    def get_schema(self) -> Dict[str, Any]:
        """
        Retorna el schema de la tool en formato OpenAI Function Calling.

        Returns:
            Dict con la estructura de parámetros de la tool
        """
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'Search query to find relevant web information. Can be about ANY topic: prices (Bitcoin, stocks), news, companies, technical specs, statistics, etc. Be specific and use clear keywords.'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Number of search results to return (1-10). Default is 5. Use lower numbers for quick checks, higher for comprehensive research.',
                        'minimum': 1,
                        'maximum': 10,
                        'default': 5
                    }
                },
                'required': ['query']
            }
        }
