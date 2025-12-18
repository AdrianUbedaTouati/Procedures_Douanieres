# -*- coding: utf-8 -*-
"""
Tool: browse_webpage

Navega a una URL y extrae información específica usando extracción progresiva con LLM.
"""

from typing import Dict, Any
from agent_ia_core.chatbots.shared import ToolDefinition
import logging
import requests
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


# ============================================================================
# DEFINICIÓN DE LA TOOL
# ============================================================================

TOOL_DEFINITION = ToolDefinition(
    name="browse_webpage",
    description=(
        "Extrae información específica de una URL. "
        "Usa después de web_search para obtener detalles exactos de las páginas encontradas."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL completa (http:// o https://). Ejemplo: 'https://example.com/article'"
            },
            "user_query": {
                "type": "string",
                "description": "Pregunta específica a responder. Ejemplo: '¿Cuál es el precio exacto del Bitcoin?'"
            },
            "max_chars": {
                "type": "integer",
                "description": "Máximo de caracteres a procesar. Por defecto: 10000",
                "minimum": 1000,
                "maximum": 50000,
                "default": 10000
            },
            "chunk_size": {
                "type": "integer",
                "description": "Tamaño de cada fragmento. Por defecto: 1250",
                "minimum": 500,
                "maximum": 5000,
                "default": 1250
            }
        },
        "required": ["url", "user_query"]
    },
    function=None,
    category="web"
)


# ============================================================================
# IMPLEMENTACIÓN
# ============================================================================

def browse_webpage(url: str, user_query: str = None, max_chars: int = 10000,
                  chunk_size: int = 1250, llm=None, **kwargs) -> Dict[str, Any]:
    """
    Navega a una URL y extrae información específica usando extracción progresiva.

    Args:
        url: URL completa de la página a navegar (debe empezar con http:// o https://)
        user_query: Pregunta específica a responder con el contenido de la página
        max_chars: Número máximo de caracteres a procesar (default: 10000)
        chunk_size: Tamaño de cada fragmento para análisis (default: 1250)
        llm: Instancia del LLM para verificación de chunks (inyectado por registry)
        **kwargs: Argumentos adicionales

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
    try:
        # Validar URL
        if not url or not isinstance(url, str):
            return {
                'success': False,
                'error': 'URL debe ser un string no vacío'
            }

        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            return {
                'success': False,
                'error': 'URL debe empezar con http:// o https://'
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

        if not text.strip():
            return {
                'success': False,
                'error': 'No se encontró contenido legible en la página'
            }

        logger.info(f"[BROWSE] Contenido extraído: {len(text)} caracteres de {url}")

        # Si se proporciona user_query y LLM, usar extracción progresiva
        if user_query and llm:
            logger.info(f"[BROWSE] Iniciando extracción progresiva con user_query: {user_query}")
            return _progressive_extraction(
                url=url,
                title=title,
                full_text=text.strip(),
                user_query=user_query,
                max_chars=max_chars,
                chunk_size=chunk_size,
                llm=llm
            )

        # Si no hay user_query o LLM, retornar contenido completo (modo legacy)
        text_limited = text[:max_chars] if len(text) > max_chars else text

        return {
            'success': True,
            'data': {
                'url': url,
                'title': title,
                'content': text_limited.strip(),
                'length': len(text_limited.strip())
            }
        }

    except requests.exceptions.Timeout:
        logger.error(f"[BROWSE] Timeout navegando a {url}")
        return {
            'success': False,
            'error': f'Timeout después de 15 segundos. La página web {url} tardó demasiado en responder.'
        }

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        logger.error(f"[BROWSE] HTTP Error {status_code} en {url}")

        if status_code == 403:
            return {
                'success': False,
                'error': f'Acceso prohibido (403). El sitio web {url} bloquea acceso automatizado.'
            }
        elif status_code == 404:
            return {
                'success': False,
                'error': f'Página no encontrada (404). La URL {url} no existe.'
            }
        elif status_code == 500:
            return {
                'success': False,
                'error': f'Error del servidor (500). El sitio web {url} está experimentando problemas técnicos.'
            }
        else:
            return {
                'success': False,
                'error': f'Error HTTP {status_code} al acceder a {url}'
            }

    except requests.exceptions.ConnectionError:
        logger.error(f"[BROWSE] Connection error a {url}")
        return {
            'success': False,
            'error': f'Error de conexión. No se puede alcanzar {url}. Verifica que la URL sea correcta y el sitio esté accesible.'
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[BROWSE] Error inesperado: {error_msg}", exc_info=True)
        return {
            'success': False,
            'error': f'Error navegando página web: {error_msg}'
        }


def _progressive_extraction(url: str, title: str, full_text: str,
                            user_query: str, max_chars: int, chunk_size: int,
                            llm) -> Dict[str, Any]:
    """
    Extrae información progresivamente, chunk por chunk, usando contexto conversacional.

    Esta es la característica BRILLANTE de browse_webpage: en lugar de enviar todo el
    contenido al LLM de una vez, lo procesa en fragmentos pequeños y DETIENE la
    extracción en cuanto encuentra la respuesta (early stopping).

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
                    "- Sé conciso pero completo. Da la respuesta exacta que el usuario necesita.\n"
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
                    f"[BROWSE] Respuesta encontrada en chunk {chunks_processed}/{(total_chars + chunk_size - 1) // chunk_size}. "
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
                    },
                    'message': 'Información específica extraída exitosamente con extracción progresiva.'
                }

        # Si llegó aquí, no encontró la respuesta en ningún chunk
        logger.warning(f"[BROWSE] No se encontró respuesta después de {chunks_processed} chunks ({chars_analyzed} chars)")

        return {
            'success': True,
            'data': {
                'url': url,
                'title': title,
                'answer': f"No se encontró información específica para responder: '{user_query}' en la página {url}. Intenta reformular la pregunta o buscar en otra URL.",
                'found': False,
                'chunks_processed': chunks_processed,
                'total_chunks': (total_chars + chunk_size - 1) // chunk_size,
                'chars_analyzed': chars_analyzed,
                'total_chars': total_chars,
                'chars_saved': 0,
                'efficiency': '0%'
            },
            'message': 'No se encontró información específica. Considera usar web_search para encontrar otras URLs relevantes.'
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[BROWSE] Error en extracción progresiva: {error_msg}", exc_info=True)
        return {
            'success': False,
            'error': f'Error durante extracción progresiva: {error_msg}'
        }


TOOL_DEFINITION.function = browse_webpage
