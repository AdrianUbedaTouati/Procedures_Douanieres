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
    Tool para extraer y leer el contenido de una página web con extracción progresiva inteligente.

    A diferencia de web_search que solo obtiene snippets, esta tool:
    - Entra en la URL proporcionada
    - Descarga el HTML completo
    - Extrae el texto principal limpio
    - Procesa el contenido en fragmentos (chunks) progresivamente
    - Usa LLM para verificar si cada chunk contiene la información buscada
    - Detiene la extracción cuando encuentra la respuesta (early stopping)
    - Devuelve la respuesta extraída (no todo el contenido)
    """

    name = "browse_webpage"
    description = """Browse and extract SPECIFIC INFORMATION from a webpage URL using progressive extraction.

WHEN TO USE THIS TOOL:
- After using web_search, to find SPECIFIC information from a URL
- When you need EXACT, DETAILED data that snippets don't provide
- To extract specific prices, dates, facts, or details from web pages
- When the user asks for "exact", "detailed", or "complete" information

WORKFLOW EXAMPLE:
1. User asks: "What is the exact Bitcoin price?"
2. You call web_search to find relevant URLs
3. You call browse_webpage(url, user_query="What is the exact Bitcoin price?")
4. The tool processes the page in chunks, verifying each one
5. When it finds the price, it returns the ANSWER directly
6. You reformulate the answer for the user in a conversational way

PROGRESSIVE EXTRACTION:
- The tool analyzes the page in chunks (configurable size per user)
- Each chunk is verified by an LLM: "Does this contain the answer?"
- If NO: continues to next chunk
- If YES: returns the extracted answer immediately (early stopping)
- Saves tokens by not processing unnecessary content

IMPORTANT:
- You MUST provide a user_query parameter (the question to answer)
- You must provide a complete URL (starting with http:// or https://)
- This tool reads static HTML content (no JavaScript rendering)
- Best for: articles, documentation, news, blogs, product pages, pricing pages
- Returns the ANSWER to your question, not the full page content

Input:
  - url: Complete URL to browse
  - user_query: The specific question you want answered from this page
Output:
  - If found: The extracted answer to the user_query
  - If not found: A message indicating the information was not found"""

    def __init__(self, default_max_chars: int = 10000, default_chunk_size: int = 1250):
        """
        Inicializa la tool.

        Args:
            default_max_chars: Número máximo de caracteres por defecto (configurable por usuario)
            default_chunk_size: Tamaño de cada fragmento para extracción progresiva
        """
        self.default_max_chars = default_max_chars
        self.default_chunk_size = default_chunk_size
        super().__init__()

    def run(self, url: str, user_query: str = None, max_chars: int = None,
            chunk_size: int = None, llm = None) -> Dict[str, Any]:
        """
        Navega a una URL y extrae información específica usando extracción progresiva.

        Args:
            url: URL completa de la página a navegar (debe empezar con http:// o https://)
            user_query: Pregunta específica a responder con el contenido de la página
            max_chars: Número máximo de caracteres a procesar (si es None, usa default_max_chars)
            chunk_size: Tamaño de cada fragmento para análisis (si es None, usa default_chunk_size)
            llm: Instancia del LLM para verificación de chunks (ChatOpenAI, ChatGemini, etc.)

        Returns:
            Dict con formato:
            {
                'success': True/False,
                'data': {
                    'url': str,
                    'title': str,
                    'answer': str (respuesta extraída) o 'content': str (si no hay user_query),
                    'found': bool (si encontró la respuesta),
                    'chunks_processed': int,
                    'chars_analyzed': int,
                    'chars_saved': int
                },
                'error': str (si success=False)
            }
        """
        # Usar defaults si no se especifican
        if max_chars is None:
            max_chars = self.default_max_chars
        if chunk_size is None:
            chunk_size = self.default_chunk_size

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

            # Si se proporciona user_query y LLM, usar extracción progresiva
            if user_query and llm:
                logger.info(f"[BROWSE] Iniciando extracción progresiva con user_query: {user_query}")
                return self._progressive_extraction(
                    url=url,
                    title=title,
                    full_text=text.strip(),
                    user_query=user_query,
                    max_chars=max_chars,
                    chunk_size=chunk_size,
                    llm=llm
                )

            # Si no hay user_query, retornar contenido completo (modo legacy)
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

    def _progressive_extraction(self, url: str, title: str, full_text: str,
                                user_query: str, max_chars: int, chunk_size: int,
                                llm) -> Dict[str, Any]:
        """
        Extrae información progresivamente, chunk por chunk, usando contexto conversacional.

        Args:
            url: URL de la página
            title: Título de la página
            full_text: Texto completo ya extraído y limpio
            user_query: Pregunta del usuario a responder
            max_chars: Límite máximo de caracteres a procesar
            chunk_size: Tamaño de cada fragmento
            llm: Instancia del LLM para verificación

        Returns:
            Dict con la respuesta extraída o mensaje de no encontrado
        """
        try:
            # Limitar el texto al max_chars
            text_to_process = full_text[:max_chars] if len(full_text) > max_chars else full_text

            # Inicializar contexto conversacional
            verification_messages = [
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente que analiza fragmentos de páginas web para extraer información específica.\n\n"
                        "INSTRUCCIONES:\n"
                        "- Si el fragmento actual NO contiene suficiente información para responder la pregunta → Responde EXACTAMENTE: 'NO'\n"
                        "- Si el fragmento actual SÍ contiene suficiente información → Responde DIRECTAMENTE con la respuesta completa y precisa\n"
                        "- No uses frases como 'Según el fragmento' o 'El texto dice'. Responde directamente.\n"
                        "- Se conciso pero completo. Da la respuesta exacta que el usuario necesita.\n"
                        "- Puedes usar información de fragmentos anteriores que ya has visto para construir una respuesta completa."
                    )
                }
            ]

            chunks_processed = 0
            chars_analyzed = 0
            total_chars = len(text_to_process)

            logger.info(f"[BROWSE] Extracción progresiva: {total_chars} chars totales, chunks de {chunk_size} chars")

            # Procesar chunks secuencialmente
            for i in range(0, len(text_to_process), chunk_size):
                chunk = text_to_process[i:i + chunk_size]
                chunks_processed += 1
                chars_analyzed += len(chunk)

                # Agregar chunk al contexto conversacional
                verification_messages.append({
                    "role": "user",
                    "content": (
                        f"Pregunta del usuario: \"{user_query}\"\n\n"
                        f"Fragmento {chunks_processed}/{(total_chars + chunk_size - 1) // chunk_size}:\n"
                        f"{chunk}\n\n"
                        f"¿Puedes responder a la pregunta con la información disponible hasta ahora?\n"
                        f"Si NO → Responde 'NO'\n"
                        f"Si SÍ → Responde directamente con la respuesta completa"
                    )
                })

                # Llamar al LLM para verificar
                logger.info(f"[BROWSE] Procesando chunk {chunks_processed} ({len(chunk)} chars)")

                response = llm.invoke(verification_messages)
                answer = response.content.strip()

                # Agregar respuesta al historial conversacional
                verification_messages.append({
                    "role": "assistant",
                    "content": answer
                })

                # Verificar si encontró la respuesta
                if answer.upper() != "NO":
                    # ¡Encontró la respuesta! Early stopping
                    chars_saved = total_chars - chars_analyzed

                    logger.info(
                        f"[BROWSE] ✓ Respuesta encontrada en chunk {chunks_processed}/{(total_chars + chunk_size - 1) // chunk_size}. "
                        f"Ahorro: {chars_saved} chars ({(chars_saved/total_chars)*100:.1f}%)"
                    )

                    return {
                        'success': True,
                        'data': {
                            'url': url,
                            'title': title,
                            'answer': answer,
                            'found': True,
                            'chunks_processed': chunks_processed,
                            'total_chunks': (total_chars + chunk_size - 1) // chunk_size,
                            'chars_analyzed': chars_analyzed,
                            'total_chars': total_chars,
                            'chars_saved': chars_saved,
                            'efficiency': f"{(chars_saved/total_chars)*100:.1f}%"
                        }
                    }

            # Si llegó aquí, no encontró la respuesta en ningún chunk
            logger.warning(f"[BROWSE] ✗ No se encontró respuesta después de {chunks_processed} chunks ({chars_analyzed} chars)")

            return {
                'success': True,
                'data': {
                    'url': url,
                    'title': title,
                    'answer': f"No se encontró información específica para responder: '{user_query}' en la página {url}",
                    'found': False,
                    'chunks_processed': chunks_processed,
                    'total_chunks': (total_chars + chunk_size - 1) // chunk_size,
                    'chars_analyzed': chars_analyzed,
                    'total_chars': total_chars,
                    'chars_saved': 0,
                    'efficiency': '0%'
                }
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[BROWSE] Error en extracción progresiva: {error_msg}", exc_info=True)
            return {
                'success': False,
                'error': f'Error during progressive extraction: {error_msg}'
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
                        'description': 'Complete URL of the webpage to browse and extract information from. Must start with http:// or https://. Example: https://example.com/article'
                    },
                    'user_query': {
                        'type': 'string',
                        'description': 'The SPECIFIC QUESTION you want answered from this webpage. Be clear and precise. Example: "What is the exact Bitcoin price?", "When does the event start?", "What are the system requirements?". This enables progressive extraction and early stopping for efficiency.'
                    },
                    'max_chars': {
                        'type': 'integer',
                        'description': 'Maximum number of characters to process from the webpage content. Default is based on user settings (typically 10000). Higher values = more content analyzed but higher token cost.',
                        'minimum': 1000,
                        'maximum': 50000,
                        'default': 10000
                    }
                },
                'required': ['url', 'user_query']
            }
        }
