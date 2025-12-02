# -*- coding: utf-8 -*-
"""
Interactive Web Browser Tool usando Playwright
Permite navegar sitios con JavaScript, hacer clicks, llenar formularios, etc.
"""

from typing import Dict, Any, List, Optional
import logging
from .base import BaseTool

logger = logging.getLogger(__name__)


class BrowseInteractiveTool(BaseTool):
    """
    Herramienta para navegar sitios web con JavaScript usando Playwright.

    Permite:
    - Cargar páginas con JavaScript renderizado
    - Hacer click en elementos (botones, enlaces, tabs)
    - Llenar y enviar formularios
    - Esperar elementos dinámicos
    - Extraer contenido después de interacciones

    Casos de uso:
    - Portales gubernamentales con navegación compleja
    - Sitios con búsquedas AJAX
    - Páginas con contenido detrás de tabs/modals
    - Formularios interactivos
    """

    name = "browse_interactive"
    description = """Navigate JavaScript-heavy websites with full browser interaction capabilities.

Use this tool when:
- Websites require clicking buttons, tabs, or links to see content
- You need to fill and submit search forms
- Content loads dynamically with AJAX/JavaScript
- Static HTML scraping (browse_webpage) doesn't work

IMPORTANT: Use browse_webpage for simple static pages. Only use this tool for JavaScript-heavy sites.

Input: URL and a query describing what information to find
Output: Extracted information from the website after smart navigation

The tool will automatically:
1. Navigate to the URL
2. Intelligently interact with the page (click, type, wait)
3. Extract the relevant information you need
4. Return structured data

Example queries:
- "Find the tender with ID 00668461-2025 in contrataciondelestado.es"
- "Search for 'software development' tenders in the government portal"
- "Get details from the 'Documentación' tab of tender XYZ"
"""

    def __init__(self, llm=None):
        """
        Inicializa la tool con un LLM opcional para extracción inteligente.

        Args:
            llm: Instancia de LLM para análisis de contenido (opcional)
        """
        self.llm = llm
        super().__init__()

    def run(
        self,
        url: str,
        query: str,
        max_steps: int = 10,
        timeout: int = 30000
    ) -> Dict[str, Any]:
        """
        Navega una página web interactivamente y extrae información.

        Args:
            url: URL de la página a navegar
            query: Qué información buscar/extraer (en lenguaje natural)
            max_steps: Máximo número de interacciones (default: 10)
            timeout: Timeout por operación en ms (default: 30000)

        Returns:
            Dict con formato:
            {
                'success': True/False,
                'data': {
                    'url': str,
                    'query': str,
                    'answer': str,  # Respuesta a la query
                    'content': str,  # Contenido relevante extraído
                    'actions_taken': List[str],  # Acciones ejecutadas
                    'final_url': str  # URL final después de navegación
                },
                'error': str (si success=False)
            }
        """
        try:
            # Validar parámetros
            if not url or not url.strip():
                return {
                    'success': False,
                    'error': 'URL cannot be empty'
                }

            if not query or not query.strip():
                return {
                    'success': False,
                    'error': 'Query cannot be empty'
                }

            # Validar que sea HTTPS
            if url.startswith('http://'):
                url = url.replace('http://', 'https://', 1)
                logger.info(f"[BROWSE_INTERACTIVE] Upgraded to HTTPS: {url}")

            logger.info(f"[BROWSE_INTERACTIVE] Navegando: {url}")
            logger.info(f"[BROWSE_INTERACTIVE] Query: {query}")

            # Importar Playwright
            try:
                from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
            except ImportError:
                return {
                    'success': False,
                    'error': 'Playwright not installed. Run: pip install playwright && playwright install chromium'
                }

            actions_taken = []

            with sync_playwright() as p:
                # Lanzar navegador (headless para producción)
                browser = p.chromium.launch(headless=True)

                try:
                    # Crear contexto con user agent realista
                    context = browser.new_context(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                        viewport={'width': 1920, 'height': 1080},
                        locale='es-ES'
                    )

                    page = context.new_page()

                    # Navegar a la página
                    logger.info(f"[BROWSE_INTERACTIVE] Cargando página...")
                    page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                    actions_taken.append(f"Navigated to {url}")

                    # Esperar a que la página se estabilice
                    page.wait_for_load_state('networkidle', timeout=timeout)
                    actions_taken.append("Waited for page to stabilize")

                    # Analizar la página y ejecutar acciones inteligentes
                    logger.info(f"[BROWSE_INTERACTIVE] Analizando página para: '{query}'")

                    # Extraer contenido inicial
                    initial_content = self._extract_page_content(page)

                    # Si el LLM está disponible, usarlo para navegación inteligente
                    if self.llm:
                        result = self._smart_navigation(
                            page=page,
                            query=query,
                            initial_content=initial_content,
                            max_steps=max_steps,
                            actions_taken=actions_taken,
                            timeout=timeout
                        )
                    else:
                        # Navegación básica sin LLM
                        result = self._basic_extraction(
                            page=page,
                            query=query,
                            initial_content=initial_content
                        )

                    final_url = page.url

                    browser.close()

                    logger.info(f"[BROWSE_INTERACTIVE] Navegación completada. {len(actions_taken)} acciones ejecutadas")

                    return {
                        'success': True,
                        'data': {
                            'url': url,
                            'query': query,
                            'answer': result['answer'],
                            'content': result['content'],
                            'actions_taken': actions_taken,
                            'final_url': final_url
                        }
                    }

                except PlaywrightTimeoutError as e:
                    browser.close()
                    return {
                        'success': False,
                        'error': f'Navigation timeout: {str(e)}. The page took too long to load or respond.'
                    }
                except Exception as e:
                    browser.close()
                    raise e

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[BROWSE_INTERACTIVE] Error: {error_msg}", exc_info=True)

            return {
                'success': False,
                'error': f'Interactive browsing error: {error_msg}'
            }

    def _extract_page_content(self, page) -> str:
        """
        Extrae el contenido textual relevante de la página.

        Args:
            page: Instancia de Playwright Page

        Returns:
            Contenido textual limpio
        """
        try:
            # Extraer texto del body, excluyendo scripts y estilos
            content = page.evaluate('''() => {
                // Remover elementos no deseados
                const unwanted = document.querySelectorAll('script, style, nav, header, footer, .cookie-banner, .advertisement');
                unwanted.forEach(el => el.remove());

                // Obtener texto del body
                return document.body.innerText;
            }''')

            # Limpiar contenido
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            clean_content = '\n'.join(lines)

            # Limitar tamaño (máx 10000 caracteres)
            if len(clean_content) > 10000:
                clean_content = clean_content[:10000] + '\n\n[... contenido truncado ...]'

            return clean_content

        except Exception as e:
            logger.warning(f"[BROWSE_INTERACTIVE] Error extrayendo contenido: {e}")
            return ""

    def _basic_extraction(
        self,
        page,
        query: str,
        initial_content: str
    ) -> Dict[str, str]:
        """
        Extracción básica sin LLM - solo retorna el contenido de la página.

        Args:
            page: Playwright Page
            query: Query del usuario
            initial_content: Contenido inicial de la página

        Returns:
            Dict con 'answer' y 'content'
        """
        return {
            'answer': f"Retrieved content from the page. Please analyze the content to answer: '{query}'",
            'content': initial_content
        }

    def _smart_navigation(
        self,
        page,
        query: str,
        initial_content: str,
        max_steps: int,
        actions_taken: List[str],
        timeout: int
    ) -> Dict[str, str]:
        """
        Navegación inteligente guiada por LLM.

        Analiza la página y decide qué acciones tomar (clicks, búsquedas, etc.)
        para encontrar la información solicitada.

        Args:
            page: Playwright Page
            query: Qué buscar
            initial_content: Contenido inicial
            max_steps: Máximo de pasos
            actions_taken: Lista de acciones para logging
            timeout: Timeout por acción

        Returns:
            Dict con 'answer' y 'content'
        """
        logger.info(f"[BROWSE_INTERACTIVE] Modo inteligente activado")

        # Construir prompt para el LLM
        navigation_prompt = f"""Estás ayudando a navegar una página web para encontrar información específica.

**PÁGINA ACTUAL:**
URL: {page.url}

**CONTENIDO VISIBLE:**
{initial_content[:3000]}

**QUERY DEL USUARIO:**
"{query}"

**TU TAREA:**
Analiza el contenido y determina si:
1. La información solicitada YA ESTÁ en la página (entonces extrae la respuesta)
2. Necesitas hacer CLICK en algo para acceder a más información
3. Necesitas BUSCAR algo en un formulario

Responde en este formato:

ACTION: [EXTRACT | CLICK | SEARCH | NOT_FOUND]
REASONING: [Explica por qué]

[Si ACTION = EXTRACT]
ANSWER: [Respuesta directa a la query del usuario basada en el contenido]

[Si ACTION = CLICK]
SELECTOR: [Descripción del elemento a clickear, ej: "botón de Documentación", "tab de Detalles"]

[Si ACTION = SEARCH]
SEARCH_TERM: [Término a buscar]
SEARCH_FIELD_SELECTOR: [Descripción del campo de búsqueda]

[Si ACTION = NOT_FOUND]
ANSWER: No se pudo encontrar la información solicitada en esta página.
"""

        try:
            # Llamar al LLM
            response = self.llm.invoke(navigation_prompt)
            llm_decision = response.content

            logger.info(f"[BROWSE_INTERACTIVE] LLM Decision:\n{llm_decision[:500]}")

            # Parsear decisión del LLM
            if 'ACTION: EXTRACT' in llm_decision:
                # La información ya está disponible
                answer = self._extract_answer_from_llm_response(llm_decision)
                actions_taken.append("LLM extracted answer from visible content")
                return {
                    'answer': answer,
                    'content': initial_content
                }

            elif 'ACTION: CLICK' in llm_decision and len(actions_taken) < max_steps:
                # Necesita hacer click en algo
                selector_desc = self._extract_selector_from_llm_response(llm_decision)

                # Intentar encontrar y clickear el elemento
                clicked = self._smart_click(page, selector_desc, timeout)

                if clicked:
                    actions_taken.append(f"Clicked on: {selector_desc}")

                    # Esperar a que se cargue el nuevo contenido
                    page.wait_for_load_state('networkidle', timeout=timeout)

                    # Extraer nuevo contenido
                    new_content = self._extract_page_content(page)

                    # Recursión con el nuevo contenido (limitado por max_steps)
                    return self._smart_navigation(
                        page=page,
                        query=query,
                        initial_content=new_content,
                        max_steps=max_steps - 1,
                        actions_taken=actions_taken,
                        timeout=timeout
                    )
                else:
                    # No se pudo clickear, retornar contenido actual
                    actions_taken.append(f"Failed to click: {selector_desc}")
                    return {
                        'answer': f"Could not interact with element: {selector_desc}. Content retrieved:",
                        'content': initial_content
                    }

            elif 'ACTION: SEARCH' in llm_decision and len(actions_taken) < max_steps:
                # Necesita buscar en un formulario
                search_term = self._extract_search_term_from_llm_response(llm_decision)

                # Intentar buscar
                searched = self._smart_search(page, search_term, timeout)

                if searched:
                    actions_taken.append(f"Searched for: {search_term}")

                    # Esperar resultados
                    page.wait_for_load_state('networkidle', timeout=timeout)

                    # Extraer resultados
                    new_content = self._extract_page_content(page)

                    return self._smart_navigation(
                        page=page,
                        query=query,
                        initial_content=new_content,
                        max_steps=max_steps - 1,
                        actions_taken=actions_taken,
                        timeout=timeout
                    )
                else:
                    actions_taken.append(f"Failed to search for: {search_term}")
                    return {
                        'answer': f"Could not perform search. Content retrieved:",
                        'content': initial_content
                    }

            else:
                # NOT_FOUND o límite de pasos alcanzado
                answer = self._extract_answer_from_llm_response(llm_decision)
                return {
                    'answer': answer if answer else "Information not found after navigation attempts.",
                    'content': initial_content
                }

        except Exception as e:
            logger.error(f"[BROWSE_INTERACTIVE] Error en navegación inteligente: {e}")
            # Fallback a extracción básica
            return self._basic_extraction(page, query, initial_content)

    def _smart_click(self, page, selector_description: str, timeout: int) -> bool:
        """
        Intenta hacer click en un elemento basándose en una descripción.

        Args:
            page: Playwright Page
            selector_description: Descripción del elemento (ej: "botón de Documentación")
            timeout: Timeout

        Returns:
            True si tuvo éxito, False si no
        """
        try:
            # Estrategias de selección en orden de prioridad
            selectors = []

            # Extraer palabras clave de la descripción
            desc_lower = selector_description.lower()

            # Si menciona "tab" o "pestaña"
            if 'tab' in desc_lower or 'pestaña' in desc_lower:
                selectors.append(f'[role="tab"]:has-text("{selector_description.split()[-1]}")')

            # Si menciona "botón" o "button"
            if 'botón' in desc_lower or 'button' in desc_lower:
                selectors.append(f'button:has-text("{selector_description.split()[-1]}")')

            # Selector genérico por texto visible
            keywords = [word for word in selector_description.split() if len(word) > 3]
            if keywords:
                selectors.append(f'text="{keywords[-1]}"')

            # Intentar cada selector
            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible(timeout=5000):
                        element.click(timeout=timeout)
                        logger.info(f"[BROWSE_INTERACTIVE] Click exitoso con selector: {selector}")
                        return True
                except Exception:
                    continue

            logger.warning(f"[BROWSE_INTERACTIVE] No se pudo encontrar elemento: {selector_description}")
            return False

        except Exception as e:
            logger.error(f"[BROWSE_INTERACTIVE] Error en click: {e}")
            return False

    def _smart_search(self, page, search_term: str, timeout: int) -> bool:
        """
        Intenta realizar una búsqueda en la página.

        Args:
            page: Playwright Page
            search_term: Término a buscar
            timeout: Timeout

        Returns:
            True si tuvo éxito, False si no
        """
        try:
            # Buscar campo de búsqueda común
            search_selectors = [
                'input[type="search"]',
                'input[name*="search" i]',
                'input[placeholder*="Buscar" i]',
                'input[placeholder*="Search" i]',
                'input[id*="search" i]',
                '#search',
                '.search-input'
            ]

            for selector in search_selectors:
                try:
                    search_field = page.locator(selector).first
                    if search_field.is_visible(timeout=5000):
                        # Llenar campo
                        search_field.fill(search_term)

                        # Presionar Enter o buscar botón submit
                        try:
                            search_field.press('Enter')
                        except Exception:
                            # Buscar botón de búsqueda
                            submit_btn = page.locator('button[type="submit"]').first
                            submit_btn.click(timeout=timeout)

                        logger.info(f"[BROWSE_INTERACTIVE] Búsqueda exitosa: {search_term}")
                        return True
                except Exception:
                    continue

            logger.warning(f"[BROWSE_INTERACTIVE] No se pudo realizar búsqueda: {search_term}")
            return False

        except Exception as e:
            logger.error(f"[BROWSE_INTERACTIVE] Error en búsqueda: {e}")
            return False

    def _extract_answer_from_llm_response(self, llm_response: str) -> str:
        """Extrae la respuesta del LLM."""
        try:
            if 'ANSWER:' in llm_response:
                answer_part = llm_response.split('ANSWER:')[1]
                # Tomar hasta el próximo campo o final
                for delimiter in ['\n\n[', '\nSELECTOR:', '\nSEARCH_TERM:']:
                    if delimiter in answer_part:
                        answer_part = answer_part.split(delimiter)[0]
                return answer_part.strip()
            return llm_response.strip()
        except Exception:
            return llm_response.strip()

    def _extract_selector_from_llm_response(self, llm_response: str) -> str:
        """Extrae el selector del LLM."""
        try:
            if 'SELECTOR:' in llm_response:
                selector = llm_response.split('SELECTOR:')[1].split('\n')[0]
                return selector.strip()
            return "link or button"
        except Exception:
            return "link or button"

    def _extract_search_term_from_llm_response(self, llm_response: str) -> str:
        """Extrae el término de búsqueda del LLM."""
        try:
            if 'SEARCH_TERM:' in llm_response:
                term = llm_response.split('SEARCH_TERM:')[1].split('\n')[0]
                return term.strip()
            return ""
        except Exception:
            return ""

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
                        'description': 'URL of the website to navigate. Must be a complete URL starting with http:// or https://'
                    },
                    'query': {
                        'type': 'string',
                        'description': 'Natural language query describing what information to find or extract from the website. Be specific about what you need. Examples: "Find tender ID 00668461-2025", "Get all documents from Documentation tab", "Search for software development contracts"'
                    },
                    'max_steps': {
                        'type': 'integer',
                        'description': 'Maximum number of interaction steps (clicks, searches) to attempt. Default is 10. Use lower values (3-5) for simple pages, higher (10-15) for complex navigation.',
                        'default': 10,
                        'minimum': 1,
                        'maximum': 15
                    },
                    'timeout': {
                        'type': 'integer',
                        'description': 'Timeout in milliseconds for each page operation (click, load, etc.). Default is 30000 (30 seconds).',
                        'default': 30000,
                        'minimum': 5000,
                        'maximum': 60000
                    }
                },
                'required': ['url', 'query']
            }
        }
