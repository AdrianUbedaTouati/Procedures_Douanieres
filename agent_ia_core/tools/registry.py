# -*- coding: utf-8 -*-
"""
Registro central de todas las tools disponibles con autodiscovery.
"""

from typing import Dict, List, Any, Optional, Callable
from .base import ToolDefinition
from . import ALL_TOOLS  # Autodiscovery de todas las tools
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registro central que mantiene todas las tools disponibles usando autodiscovery.

    Responsable de:
    - Crear instancias de las tools automáticamente
    - Proporcionar schemas para el LLM
    - Ejecutar tools por nombre
    - Generar descripción para el reviewer
    """

    def __init__(self, retriever, db_session=None, user=None, max_retries: int = 3):
        """
        Inicializa el registro con autodiscovery de todas las tools.

        Args:
            retriever: Retriever de ChromaDB para búsqueda vectorial
            db_session: Sesión de base de datos Django (opcional)
            user: Usuario de Django para tools de contexto (opcional)
            max_retries: Número máximo de reintentos por tool en caso de fallo (default: 3)
        """
        self.retriever = retriever
        self.db_session = db_session
        self.user = user
        self.max_retries = max_retries
        self.tool_definitions: Dict[str, ToolDefinition] = {}
        self._register_all_tools()

    def _register_all_tools(self):
        """Registra todas las tools autodescubiertas."""
        logger.info("[REGISTRY] Registrando tools con autodiscovery...")

        # Registrar todas las tools descubiertas automáticamente
        for tool_def in ALL_TOOLS:
            self.tool_definitions[tool_def.name] = tool_def

        logger.info(f"[REGISTRY] {len(self.tool_definitions)} tools autodescubiertas: {list(self.tool_definitions.keys())}")

        # Verificar tools opcionales basadas en configuración de usuario
        if self.user:
            # Tools de contexto ya están en ALL_TOOLS (get_company_info, get_tenders_summary)
            logger.info("[REGISTRY] Tools de contexto disponibles (user proporcionado)")

            # Grading: Filtra documentos irrelevantes
            if getattr(self.user, 'use_grading', False):
                logger.info("[REGISTRY] ⚠ Grading tool detectada en configuración pero no implementada en nuevo sistema")

            # Verification: Valida campos críticos con XML
            if getattr(self.user, 'use_verification', False):
                logger.info("[REGISTRY] ⚠ Verification tool detectada en configuración pero no implementada en nuevo sistema")

            # Web Search: Búsqueda en internet
            if getattr(self.user, 'use_web_search', False):
                logger.info("[REGISTRY] ⚠ Web search tool detectada en configuración pero no implementada en nuevo sistema")

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """
        Obtiene una tool definition por nombre.

        Args:
            name: Nombre de la tool

        Returns:
            ToolDefinition o None si no existe
        """
        return self.tool_definitions.get(name)

    def get_all_tools(self) -> Dict[str, ToolDefinition]:
        """
        Obtiene todas las tool definitions.

        Returns:
            Diccionario con todas las tools
        """
        return self.tool_definitions.copy()

    def get_tool_names(self) -> List[str]:
        """
        Obtiene nombres de todas las tools.

        Returns:
            Lista de nombres
        """
        return list(self.tool_definitions.keys())

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """
        Obtiene schemas de todas las tools en formato OpenAI.

        Returns:
            Lista de schemas
        """
        return [tool_def.to_openai_format() for tool_def in self.tool_definitions.values()]

    def get_ollama_tools(self) -> List[Dict[str, Any]]:
        """
        Obtiene todas las tools en formato Ollama.

        Returns:
            Lista de tools en formato Ollama
        """
        return [tool_def.to_openai_format() for tool_def in self.tool_definitions.values()]

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Obtiene todas las tools en formato OpenAI."""
        return [tool_def.to_openai_format() for tool_def in self.tool_definitions.values()]

    def get_gemini_tools(self) -> List[Dict[str, Any]]:
        """Obtiene todas las tools en formato Google Gemini."""
        return [tool_def.to_gemini_format() for tool_def in self.tool_definitions.values()]

    def get_tools_for_provider(self, provider: str) -> List[Dict[str, Any]]:
        """Obtiene todas las tools en el formato del proveedor especificado."""
        if provider == "ollama":
            return self.get_ollama_tools()
        elif provider == "openai":
            return self.get_openai_tools()
        elif provider == "google":
            return self.get_gemini_tools()
        else:
            logger.warning(f"Proveedor desconocido: {provider}, usando formato OpenAI")
            return self.get_openai_tools()

    def get_reviewer_tools_description(self) -> str:
        """
        Genera descripción de todas las tools disponibles para el reviewer.

        Returns:
            String con formato de lista de tools para el prompt del reviewer
        """
        tools_list = []
        for tool_def in self.tool_definitions.values():
            tools_list.append(tool_def.get_reviewer_format())

        return "\n".join(tools_list)

    def execute_tool(self, name: str, max_retries: int = None, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta una tool por nombre con sistema de reintentos.

        Args:
            name: Nombre de la tool
            max_retries: Número máximo de reintentos en caso de fallo (default: None = usa self.max_retries)
            **kwargs: Parámetros para la tool

        Returns:
            Dict con resultado de la ejecución
        """
        if max_retries is None:
            max_retries = self.max_retries

        tool_def = self.get_tool(name)

        if not tool_def:
            logger.error(f"[REGISTRY] Tool '{name}' no encontrada")
            return {
                'success': False,
                'error': f"Tool '{name}' no existe. Tools disponibles: {self.get_tool_names()}"
            }

        # Inyectar dependencias según la tool
        injected_kwargs = kwargs.copy()

        # Inyectar retriever para tools de búsqueda
        if 'retriever' in tool_def.function.__code__.co_varnames:
            injected_kwargs['retriever'] = self.retriever

        # Inyectar db_session para tools de base de datos
        if 'db_session' in tool_def.function.__code__.co_varnames:
            injected_kwargs['db_session'] = self.db_session

        # Inyectar user para tools de contexto
        if 'user' in tool_def.function.__code__.co_varnames:
            injected_kwargs['user'] = self.user

        # Sistema de reintentos
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    logger.warning(f"[REGISTRY] Reintento {attempt}/{max_retries} para tool '{name}'")
                else:
                    logger.info(f"[REGISTRY] Ejecutando tool '{name}'...")

                # Ejecutar la función de la tool
                result = tool_def.function(**injected_kwargs)

                # Verificar si el resultado indica éxito
                if isinstance(result, dict):
                    if result.get('success', True):  # Si no hay campo 'success', asumimos éxito
                        if attempt > 1:
                            logger.info(f"[REGISTRY] ✓ Tool '{name}' exitosa en intento {attempt}/{max_retries}")
                            result['total_attempts'] = attempt
                            result['retries_exhausted'] = False
                        return result
                    else:
                        # La tool falló
                        last_error = result.get('error', 'Error desconocido')
                        logger.warning(f"[REGISTRY] Tool '{name}' falló (intento {attempt}/{max_retries}): {last_error}")

                        if attempt == max_retries:
                            logger.error(f"[REGISTRY] ✗ Tool '{name}' falló después de {max_retries} intentos")
                            result['retries_exhausted'] = True
                            result['total_attempts'] = attempt
                            return result
                else:
                    # Resultado no estructurado, asumir éxito
                    return result

            except Exception as e:
                last_error = str(e)
                logger.error(f"[REGISTRY] Excepción en tool '{name}' (intento {attempt}/{max_retries}): {e}", exc_info=True)

                if attempt == max_retries:
                    logger.error(f"[REGISTRY] ✗ Tool '{name}' falló después de {max_retries} intentos con excepción")
                    return {
                        'success': False,
                        'error': f"Error después de {max_retries} intentos: {last_error}",
                        'retries_exhausted': True,
                        'total_attempts': attempt,
                        'last_exception': str(e)
                    }

        return {
            'success': False,
            'error': f"Error desconocido después de {max_retries} intentos: {last_error}",
            'retries_exhausted': True,
            'total_attempts': max_retries
        }

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
        return f"<ToolRegistry({len(self.tool_definitions)} tools)>"
