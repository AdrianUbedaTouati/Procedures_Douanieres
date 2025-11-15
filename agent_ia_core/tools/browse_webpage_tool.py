# -*- coding: utf-8 -*-
"""
Tool para navegar y extraer contenido de páginas web.
Utiliza BeautifulSoup + Requests para scraping.
"""

from typing import Dict, Any
import logging
from .base import BaseTool
import requests
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


class BrowseWebpageTool(BaseTool):
    """
    Tool para extraer y leer el contenido completo de una página web.

    A diferencia de web_search que solo obtiene snippets, esta tool:
    - Entra en la URL proporcionada
    - Descarga el HTML completo
    - Extrae el texto principal limpio
    - Devuelve el contenido para análisis del LLM
    """

    name = "browse_webpage"
    description = """Browse and extract the COMPLETE content from a specific webpage URL.

WHEN TO USE THIS TOOL:
- After using web_search, to read the FULL content of a URL (not just the snippet)
- When you need EXACT, DETAILED information that snippets don't provide
- To get the complete text of articles, documentation, news, or product pages
- When the user asks for "exact", "detailed", or "complete" information

WORKFLOW EXAMPLE:
1. User asks: "What is the exact Bitcoin price?"
2. You call web_search to find relevant URLs
3. You call browse_webpage with the URL to get the FULL page content
4. You extract the exact price from the complete content

This tool downloads the webpage, extracts the main text content, and returns it cleaned and formatted.
Unlike web_search (which only gives snippets), this tool gives you the COMPLETE page content.

IMPORTANT:
- Use this AFTER web_search to get full details
- You must provide a complete URL (starting with http:// or https://)
- This tool reads static HTML content (no JavaScript rendering)
- Best for: articles, documentation, news, blogs, product pages, pricing pages

Input: A complete URL to browse and extract content from.
Output: The main text content of the webpage, cleaned and formatted."""

    def __init__(self, default_max_chars: int = 10000):
        """
        Inicializa la tool.

        Args:
            default_max_chars: Número máximo de caracteres por defecto (configurable por usuario)
        """
        self.default_max_chars = default_max_chars
        super().__init__()

    def run(self, url: str, max_chars: int = None) -> Dict[str, Any]:
        """
        Navega a una URL y extrae su contenido principal.

        Args:
            url: URL completa de la página a navegar (debe empezar con http:// o https://)
            max_chars: Número máximo de caracteres a retornar (si es None, usa default_max_chars)

        Returns:
            Dict con formato:
            {
                'success': True/False,
                'data': {
                    'url': str,
                    'title': str,
                    'content': str (texto limpio),
                    'length': int (caracteres)
                },
                'error': str (si success=False)
            }
        """
        # Usar default_max_chars si no se especifica max_chars
        if max_chars is None:
            max_chars = self.default_max_chars

        try:
            # Validar URL
            if not url or not isinstance(url, str):
                return {
                    'success': False,
                    'error': 'URL must be a non-empty string'
                }

            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                return {
                    'success': False,
                    'error': 'URL must start with http:// or https://'
                }

            logger.info(f"[BROWSE] Navegando a: {url}")

            # Configurar headers para simular un navegador
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }

            # Realizar request con timeout
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()

            # Detectar encoding
            if response.encoding is None or response.encoding == 'ISO-8859-1':
                # Intentar detectar desde content-type o meta tags
                response.encoding = response.apparent_encoding

            # Parsear HTML con BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extraer título
            title = ''
            if soup.title:
                title = soup.title.string.strip() if soup.title.string else ''

            # Si no hay title tag, buscar h1
            if not title and soup.h1:
                title = soup.h1.get_text().strip()

            # Eliminar scripts, styles, y otros elementos no deseados
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
                element.decompose()

            # Intentar encontrar el contenido principal
            # Priorizar elementos semánticos HTML5
            main_content = None
            for tag in ['main', 'article', 'div[role="main"]', '.content', '.main-content', '#content', '#main']:
                main_content = soup.select_one(tag)
                if main_content:
                    break

            # Si no se encuentra contenido principal, usar body
            if not main_content:
                main_content = soup.body if soup.body else soup

            # Extraer texto
            text = main_content.get_text(separator='\n', strip=True)

            # Limpiar texto
            # Eliminar líneas vacías múltiples
            text = re.sub(r'\n\s*\n', '\n\n', text)
            # Eliminar espacios múltiples
            text = re.sub(r' +', ' ', text)
            # Eliminar tabulaciones
            text = re.sub(r'\t+', ' ', text)

            # Limitar longitud
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n\n[Content truncated. Total length: {len(text)} chars, showing first {max_chars} chars]"

            if not text.strip():
                return {
                    'success': False,
                    'error': 'No readable content found on the page'
                }

            logger.info(f"[BROWSE] Contenido extraído: {len(text)} caracteres de {url}")

            return {
                'success': True,
                'data': {
                    'url': url,
                    'title': title,
                    'content': text.strip(),
                    'length': len(text.strip())
                }
            }

        except requests.exceptions.Timeout:
            logger.error(f"[BROWSE] Timeout navegando a {url}")
            return {
                'success': False,
                'error': f'Request timeout after 15 seconds. The webpage {url} took too long to respond.'
            }

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            logger.error(f"[BROWSE] HTTP Error {status_code} en {url}")

            if status_code == 403:
                return {
                    'success': False,
                    'error': f'Access forbidden (403). The website {url} blocks automated access.'
                }
            elif status_code == 404:
                return {
                    'success': False,
                    'error': f'Page not found (404). The URL {url} does not exist.'
                }
            elif status_code == 500:
                return {
                    'success': False,
                    'error': f'Server error (500). The website {url} is experiencing technical issues.'
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP error {status_code} when accessing {url}'
                }

        except requests.exceptions.ConnectionError:
            logger.error(f"[BROWSE] Connection error a {url}")
            return {
                'success': False,
                'error': f'Connection error. Cannot reach {url}. Check if the URL is correct and the site is accessible.'
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[BROWSE] Error inesperado: {error_msg}", exc_info=True)
            return {
                'success': False,
                'error': f'Error browsing webpage: {error_msg}'
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
                    'url': {
                        'type': 'string',
                        'description': 'Complete URL of the webpage to browse and extract content from. Must start with http:// or https://. Example: https://example.com/article'
                    },
                    'max_chars': {
                        'type': 'integer',
                        'description': 'Maximum number of characters to return from the webpage content. Default is 10000. Use lower values for quick summaries, higher for detailed analysis.',
                        'minimum': 1000,
                        'maximum': 50000,
                        'default': 10000
                    }
                },
                'required': ['url']
            }
        }
