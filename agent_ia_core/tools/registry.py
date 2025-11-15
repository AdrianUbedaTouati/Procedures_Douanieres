# -*- coding: utf-8 -*-
"""
Registro central de todas las tools disponibles.
"""

from typing import Dict, List, Any, Optional
from .base import BaseTool
from .search_tools import SearchTendersTool, FindByBudgetTool
from .tender_tools import GetTenderDetailsTool
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registro central que mantiene todas las tools disponibles.
    Responsable de:
    - Crear instancias de las tools
    - Proporcionar schemas para el LLM
    - Ejecutar tools por nombre
    """

    def __init__(self, retriever, db_session=None, user=None):
        """
        Inicializa el registro con todas las tools.

        Args:
            retriever: Retriever de ChromaDB para búsqueda vectorial
            db_session: Sesión de base de datos Django (opcional)
            user: Usuario de Django para tools de contexto (opcional)
        """
        self.retriever = retriever
        self.db_session = db_session
        self.user = user
        self.tools: Dict[str, BaseTool] = {}
        self._register_all_tools()

    def _register_all_tools(self):
        """Registra todas las tools disponibles."""
        logger.info("[REGISTRY] Registrando tools...")

        from .search_tools import (
            FindByDeadlineTool,
            FindByCPVTool,
            FindByLocationTool,
            GetStatisticsTool
        )
        from .tender_tools import GetTenderXMLTool, CompareTendersTool
        from .context_tools import GetCompanyInfoTool, GetTendersSummaryTool

        # Tools de contexto (solo si hay usuario)
        if self.user:
            self.tools['get_company_info'] = GetCompanyInfoTool(self.user)
            self.tools['get_tenders_summary'] = GetTendersSummaryTool(self.user)
            logger.info("[REGISTRY] Tools de contexto registradas (get_company_info, get_tenders_summary)")

        # Tools de búsqueda
        self.tools['search_tenders'] = SearchTendersTool(self.retriever)
        self.tools['find_by_budget'] = FindByBudgetTool(self.db_session)
        self.tools['find_by_deadline'] = FindByDeadlineTool(self.db_session)
        self.tools['find_by_cpv'] = FindByCPVTool(self.retriever)
        self.tools['find_by_location'] = FindByLocationTool(self.retriever)

        # Tools de información detallada
        self.tools['get_tender_details'] = GetTenderDetailsTool(self.db_session)
        self.tools['get_tender_xml'] = GetTenderXMLTool(self.db_session)

        # Tools de análisis
        self.tools['get_statistics'] = GetStatisticsTool(self.db_session)
        self.tools['compare_tenders'] = CompareTendersTool(self.db_session)

        # Tools de grading y verification (solo si el usuario las activa)
        if self.user:
            # Grading: Filtra documentos irrelevantes
            if getattr(self.user, 'use_grading', False):
                from .grading_tool import GradeDocumentsTool
                # Necesitamos el LLM para grading, lo obtenemos del agente
                # Por ahora registramos la clase, el LLM se inyectará después
                self.tools['grade_documents'] = None  # Será inicializado por el agente
                logger.info("[REGISTRY] ✓ Grading tool habilitada (use_grading=True)")

            # Verification: Valida campos críticos con XML
            if getattr(self.user, 'use_verification', False):
                from .verification_tool import VerifyFieldsTool
                self.tools['verify_fields'] = VerifyFieldsTool()
                logger.info("[REGISTRY] ✓ Verification tool habilitada (use_verification=True)")

            # Web Search: Búsqueda en internet usando Google Custom Search API
            if getattr(self.user, 'use_web_search', False):
                google_search_api_key = getattr(self.user, 'google_search_api_key', None)
                google_search_engine_id = getattr(self.user, 'google_search_engine_id', None)

                if google_search_api_key and google_search_engine_id:
                    from .web_search_tool import GoogleWebSearchTool
                    self.tools['web_search'] = GoogleWebSearchTool(
                        api_key=google_search_api_key,
                        engine_id=google_search_engine_id
                    )
                    logger.info("[REGISTRY] ✓ Web search tool habilitada (use_web_search=True, credenciales OK)")

                    # Browse Webpage: Navega y extrae contenido completo de páginas web
                    # Se habilita cuando use_web_search está activo Y hay credenciales de Google Search
                    from .browse_webpage_tool import BrowseWebpageTool
                    browse_max_chars = getattr(self.user, 'browse_max_chars', 10000)
                    browse_chunk_size = getattr(self.user, 'browse_chunk_size', 1250)
                    self.tools['browse_webpage'] = BrowseWebpageTool(
                        default_max_chars=browse_max_chars,
                        default_chunk_size=browse_chunk_size
                    )
                    logger.info(
                        f"[REGISTRY] ✓ Browse webpage tool habilitada "
                        f"(use_web_search=True, max_chars={browse_max_chars}, chunk_size={browse_chunk_size})"
                    )

                    # Browse Interactive: Navegador interactivo con Playwright para sitios JavaScript
                    # Se habilita automáticamente cuando use_web_search está activo
                    from .browse_interactive_tool import BrowseInteractiveTool
                    self.tools['browse_interactive'] = BrowseInteractiveTool()
                    logger.info("[REGISTRY] ✓ Browse interactive tool habilitada (use_web_search=True, Playwright)")
                else:
                    logger.warning(
                        "[REGISTRY] ⚠ use_web_search=True pero faltan credenciales. "
                        f"API Key: {'OK' if google_search_api_key else 'FALTA'}, "
                        f"Engine ID: {'OK' if google_search_engine_id else 'FALTA'}"
                    )

        logger.info(f"[REGISTRY] {len(self.tools)} tools registradas: {list(self.tools.keys())}")

    def initialize_grading_tool(self, llm):
        """
        Inicializa la grading tool con el LLM del agente.

        Este método debe ser llamado por el agente después de crear el registry,
        para inyectar el LLM necesario para la evaluación de relevancia.

        Args:
            llm: Instancia del LLM (ChatOllama, ChatOpenAI, etc.)
        """
        if 'grade_documents' in self.tools and self.tools['grade_documents'] is None:
            from .grading_tool import GradeDocumentsTool
            self.tools['grade_documents'] = GradeDocumentsTool(llm)
            logger.info("[REGISTRY] GradeDocumentsTool inicializada con LLM")

        # Guardar referencia al LLM para browse_webpage y browse_interactive
        self.llm = llm

        # Inyectar LLM a browse_interactive si existe
        if 'browse_interactive' in self.tools:
            self.tools['browse_interactive'].llm = llm
            logger.info("[REGISTRY] BrowseInteractiveTool inicializada con LLM para navegación inteligente")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Obtiene una tool por nombre.

        Args:
            name: Nombre de la tool

        Returns:
            Instancia de BaseTool o None si no existe
        """
        return self.tools.get(name)

    def get_all_tools(self) -> Dict[str, BaseTool]:
        """
        Obtiene todas las tools.

        Returns:
            Diccionario con todas las tools
        """
        return self.tools.copy()

    def get_tool_names(self) -> List[str]:
        """
        Obtiene nombres de todas las tools.

        Returns:
            Lista de nombres
        """
        return list(self.tools.keys())

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """
        Obtiene schemas de todas las tools en formato OpenAI.

        Returns:
            Lista de schemas
        """
        return [tool.get_schema() for tool in self.tools.values()]

    def get_ollama_tools(self) -> List[Dict[str, Any]]:
        """
        Obtiene todas las tools en formato Ollama.

        Returns:
            Lista de tools en formato Ollama:
            [
                {
                    'type': 'function',
                    'function': {...schema...}
                },
                ...
            ]
        """
        return [tool.to_ollama_tool() for tool in self.tools.values()]

    def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta una tool por nombre.

        Args:
            name: Nombre de la tool
            **kwargs: Parámetros para la tool

        Returns:
            Dict con resultado de la ejecución
        """
        tool = self.get_tool(name)

        if not tool:
            logger.error(f"[REGISTRY] Tool '{name}' no encontrada")
            return {
                'success': False,
                'error': f"Tool '{name}' no existe. Tools disponibles: {self.get_tool_names()}"
            }

        # Si la tool es browse_webpage y tiene LLM disponible, inyectarlo
        if name == 'browse_webpage' and hasattr(self, 'llm') and self.llm:
            kwargs['llm'] = self.llm
            logger.info(f"[REGISTRY] Inyectando LLM a browse_webpage para extracción progresiva")

        # Si la tool es browse_interactive, el LLM ya está inyectado en __init__
        # No necesita inyección en kwargs porque es parte del estado de la tool

        logger.info(f"[REGISTRY] Ejecutando tool '{name}'...")
        return tool.execute_safe(**kwargs)

    def execute_tool_calls(self, tool_calls: List[Dict]) -> List[Dict[str, Any]]:
        """
        Ejecuta múltiples tool calls.

        Args:
            tool_calls: Lista de tool calls en formato:
                [
                    {
                        'function': {
                            'name': str,
                            'arguments': dict
                        }
                    },
                    ...
                ]

        Returns:
            Lista de resultados
        """
        results = []

        for tool_call in tool_calls:
            function = tool_call.get('function', {})
            name = function.get('name')
            arguments = function.get('arguments', {})

            if not name:
                results.append({
                    'success': False,
                    'error': 'Tool call sin nombre'
                })
                continue

            result = self.execute_tool(name, **arguments)
            results.append({
                'tool': name,
                'arguments': arguments,
                'result': result
            })

        return results

    def __repr__(self):
        return f"<ToolRegistry({len(self.tools)} tools)>"

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Obtiene todas las tools en formato OpenAI."""
        from .schema_converters import SchemaConverter
        return [SchemaConverter.to_openai_format(tool.get_schema()) for tool in self.tools.values()]

    def get_gemini_tools(self) -> List[Dict[str, Any]]:
        """Obtiene todas las tools en formato Google Gemini."""
        from .schema_converters import SchemaConverter
        return [SchemaConverter.to_gemini_format(tool.get_schema()) for tool in self.tools.values()]

    def get_tools_for_provider(self, provider: str) -> List[Dict[str, Any]]:
        """Obtiene todas las tools en el formato del proveedor especificado."""
        if provider == "ollama":
            return self.get_ollama_tools()
        elif provider == "openai":
            return self.get_openai_tools()
        elif provider == "google":
            return self.get_gemini_tools()
        else:
            logger.warning(f"Proveedor desconocido: {provider}, usando formato Ollama")
            return self.get_ollama_tools()
