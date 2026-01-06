# -*- coding: utf-8 -*-
"""
Agente con Function Calling para Ollama, OpenAI y Google Gemini.
Versión genérica del sistema de chat con tools dinámicas.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import sys
import logging
import json
from datetime import datetime

# Importar infraestructura compartida
from agent_ia_core.chatbots.shared import ToolRegistry, ToolDefinition

# Importar tools locales de este chatbot
from .tools import ALL_TOOLS

# Imports de LLMs
try:
    from langchain_ollama import ChatOllama
except ImportError:
    ChatOllama = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_current_datetime() -> str:
    """
    Devuelve la fecha y hora actual en formato legible para el LLM.
    """
    now = datetime.now()
    return f"Fecha actual: {now.strftime('%Y-%m-%d')} | Hora: {now.strftime('%H:%M:%S')}"


class FunctionCallingAgent:
    """
    Agente que usa Function Calling para decidir qué tools usar.

    Flujo:
    1. Usuario hace una pregunta
    2. LLM decide qué tools necesita (0, 1 o múltiples)
    3. Sistema ejecuta las tools
    4. LLM genera respuesta final usando resultados

    Soporta:
    - Ollama (qwen2.5:7b y otros con function calling)
    - OpenAI (GPT-4, GPT-3.5)
    - Google Gemini
    """

    def __init__(
        self,
        llm_provider: str,
        llm_model: str,
        llm_api_key: Optional[str],
        user=None,
        max_iterations: int = 5,
        temperature: float = 0.3,
        chat_logger=None,
        expedition_id: int = None,
        etape_id: int = None,
        system_prompt: Optional[str] = None
    ):
        """
        Inicializa el agente con function calling.

        Args:
            llm_provider: Proveedor ("ollama", "openai", "google")
            llm_model: Modelo específico
            llm_api_key: API key (no necesaria para Ollama)
            user: Usuario de Django para tools de contexto
            max_iterations: Máximo de iteraciones del loop
            temperature: Temperatura del LLM
            chat_logger: ChatLogger instance para logging detallado (opcional)
            expedition_id: ID de la expedición para tools de contexto (opcional)
            etape_id: ID de la etapa para tools de contexto (opcional)
            system_prompt: System prompt personalizado (opcional). Si no se proporciona, usa el genérico.
        """
        self.llm_provider = llm_provider.lower()
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.user = user
        self.chat_logger = chat_logger
        self.expedition_id = expedition_id
        self.etape_id = etape_id
        self.custom_system_prompt = system_prompt

        # Validaciones
        if self.llm_provider not in ['ollama', 'openai', 'google']:
            raise ValueError(f"Proveedor '{llm_provider}' no soportado. Use: ollama, openai, google")

        if self.llm_provider != 'ollama' and not llm_api_key:
            raise ValueError(f"API key requerida para {llm_provider}")

        # Inicializar LLM
        logger.info(f"[AGENT] Inicializando {llm_provider} - {llm_model}")
        self.llm = self._create_llm()

        # Inicializar tool registry con usuario
        logger.info(f"[AGENT] Inicializando tool registry...")

        # Extraer credenciales de Google para web tools
        google_api_key = getattr(user, 'google_search_api_key', None) if user else None
        google_engine_id = getattr(user, 'google_search_engine_id', None) if user else None

        self.tool_registry = ToolRegistry(
            all_tools=ALL_TOOLS,
            retriever=None,
            db_session=None,
            user=user,
            llm=self.llm,
            google_api_key=google_api_key,
            google_engine_id=google_engine_id,
            chat_logger=self.chat_logger,
            expedition_id=self.expedition_id,
            etape_id=self.etape_id
        )

        logger.info(f"[AGENT] Agente inicializado con {len(self.tool_registry.tool_definitions)} tools")

    def _create_llm(self):
        """Crea la instancia del LLM según el proveedor."""
        if self.llm_provider == 'ollama':
            if not ChatOllama:
                raise ImportError("langchain-ollama no instalado. Ejecuta: pip install langchain-ollama")

            return ChatOllama(
                model=self.llm_model,
                temperature=self.temperature,
                base_url="http://localhost:11434"
            )

        elif self.llm_provider == 'openai':
            if not ChatOpenAI:
                raise ImportError("langchain-openai no instalado. Ejecuta: pip install langchain-openai")

            return ChatOpenAI(
                model=self.llm_model,
                temperature=self.temperature,
                openai_api_key=self.llm_api_key
            )

        elif self.llm_provider == 'google':
            if not ChatGoogleGenerativeAI:
                raise ImportError("langchain-google-genai no instalado. Ejecuta: pip install langchain-google-genai")

            model_name = self.llm_model.replace("models/", "")

            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=self.temperature,
                google_api_key=self.llm_api_key
            )

    def query(
        self,
        question: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta una query con function calling.

        Args:
            question: Pregunta del usuario
            conversation_history: Historial de conversación previo

        Returns:
            Dict con:
                - answer: Respuesta final
                - tools_used: Lista de tools usadas
                - iterations: Número de iteraciones
                - metadata: Info adicional
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"[QUERY] {question}")
        if conversation_history:
            logger.info(f"[QUERY] Historial: {len(conversation_history)} mensajes")
        logger.info(f"{'='*80}\n")

        # Preparar mensajes
        messages = self._prepare_messages(question, conversation_history)

        # Loop de function calling
        iteration = 0
        tools_used = []
        tool_results_history = []

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"\n--- ITERACIÓN {iteration} ---")

            # Llamar al LLM con tools
            response = self._call_llm_with_tools(messages)

            # ¿Hay tool calls?
            tool_calls = response.get('tool_calls', [])

            if not tool_calls:
                # No hay tool calls, tenemos la respuesta final
                final_answer = response.get('content', '')
                logger.info(f"[ANSWER] Respuesta final generada")

                # LOG: Flujo de ejecución y resumen final
                if self.chat_logger:
                    self.chat_logger.log_execution_flow(iteration, "Generate final answer", [])
                    self.chat_logger.log_tool_execution_summary(tool_results_history)

                return {
                    'answer': final_answer,
                    'tools_used': tools_used,
                    'tools_failed': self._extract_failed_tools(tool_results_history),
                    'tool_results': tool_results_history,
                    'iterations': iteration,
                    'documents': [],
                    'route': 'function_calling',
                    'verified_fields': [],
                    'metadata': {
                        'provider': self.llm_provider,
                        'model': self.llm_model,
                        'max_iterations': self.max_iterations
                    }
                }

            # Ejecutar tool calls
            logger.info(f"[TOOLS] LLM solicitó {len(tool_calls)} tool(s)")

            # LOG: Flujo de ejecución con las tools que se van a llamar
            if self.chat_logger:
                tools_to_call = [tc.get('function', {}).get('name', 'unknown') for tc in tool_calls]
                self.chat_logger.log_execution_flow(iteration, f"Call {len(tool_calls)} tool(s)", tools_to_call)

            # Pasar conversation_history y tool_calls_history al registry
            results = self.tool_registry.execute_tool_calls(
                tool_calls,
                conversation_history=conversation_history,
                tool_calls_history=tool_results_history
            )

            # Registrar tools usadas
            for idx, result in enumerate(results):
                tool_name = result.get('tool')

                # LOG: Tool call y resultado
                if self.chat_logger:
                    tool_args = result.get('arguments', {})
                    tool_result = result.get('result', {})
                    success = tool_result.get('success', False) if isinstance(tool_result, dict) else True

                    self.chat_logger.log_tool_call(tool_name, tool_args, iteration=iteration)
                    self.chat_logger.log_tool_result(tool_name, tool_result, iteration=iteration, success=success)

                if tool_name and tool_name not in tools_used:
                    tools_used.append(tool_name)
                tool_results_history.append(result)

            # Añadir tool results al historial de mensajes
            messages = self._add_tool_results_to_messages(
                messages,
                response,
                tool_calls,
                results
            )

        # Max iterations alcanzado
        logger.warning(f"[AGENT] Máximo de iteraciones ({self.max_iterations}) alcanzado")

        if self.chat_logger:
            self.chat_logger.log_tool_execution_summary(tool_results_history)

        return {
            'answer': 'Lo siento, no pude completar la tarea en el número de pasos permitidos. Intenta hacer la pregunta de otra manera o más específica.',
            'tools_used': tools_used,
            'tools_failed': self._extract_failed_tools(tool_results_history),
            'tool_results': tool_results_history,
            'iterations': iteration,
            'documents': [],
            'route': 'function_calling',
            'verified_fields': [],
            'metadata': {
                'provider': self.llm_provider,
                'model': self.llm_model,
                'max_iterations_reached': True
            }
        }

    def _prepare_messages(
        self,
        question: str,
        conversation_history: Optional[List[Dict]]
    ) -> List[Dict]:
        """Prepara los mensajes para el LLM."""
        messages = []

        # Usar system prompt personalizado si existe, sino el genérico
        if self.custom_system_prompt:
            # System prompt personalizado (ej: TARIC classification)
            system_prompt = self.custom_system_prompt
        else:
            # System prompt genérico por defecto
            system_prompt_parts = [
                "Eres un asistente de IA inteligente y versátil. Puedes ayudar con cualquier tema y tienes acceso a herramientas especializadas.",
                "",
                f"CONTEXTO TEMPORAL: {get_current_datetime()}",
                "",
                "HERRAMIENTAS DISPONIBLES:",
            ]

            # Añadir web_search y browse_webpage si están disponibles
            if 'web_search' in self.tool_registry.tool_definitions:
                system_prompt_parts.extend([
                    "- web_search: Buscar información en internet (clima, noticias, precios, datos actuales)",
                    "- browse_webpage: Navegar a una URL específica para extraer contenido detallado",
                ])

            system_prompt_parts.extend([
                "",
                "INSTRUCCIONES:",
                "- Usa las herramientas cuando necesites información actualizada o específica",
                "- Para preguntas sobre el tiempo, noticias, precios actuales → usa web_search",
                "- Si ya tienes la información necesaria, responde directamente",
                "- Sé útil, claro y conversacional",
                "",
                "Ejemplos de cuándo usar herramientas:",
                '- "¿Qué tiempo hace en Madrid?" → USA web_search',
                '- "Precio del Bitcoin" → USA web_search',
                '- "Noticias sobre inteligencia artificial" → USA web_search',
                '- "Explícame qué es Python" → Responde directamente (conocimiento general)',
            ])

            system_prompt = "\n".join(system_prompt_parts)

        messages.append({
            'role': 'system',
            'content': system_prompt
        })

        # Añadir historial si existe
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })

        # Añadir pregunta actual
        messages.append({
            'role': 'user',
            'content': question
        })

        return messages

    def _call_llm_with_tools(self, messages: List[Dict]) -> Dict[str, Any]:
        """Llama al LLM con las tools disponibles."""
        if self.llm_provider == 'ollama':
            return self._call_ollama_with_tools(messages)
        elif self.llm_provider == 'openai':
            return self._call_openai_with_tools(messages)
        elif self.llm_provider == 'google':
            return self._call_gemini_with_tools(messages)

    def _call_ollama_with_tools(self, messages: List[Dict]) -> Dict[str, Any]:
        """Llama a Ollama con function calling nativo."""
        import ollama

        try:
            response = ollama.chat(
                model=self.llm_model,
                messages=messages,
                tools=self.tool_registry.get_ollama_tools()
            )

            message = response.get('message', {})

            return {
                'content': message.get('content', ''),
                'tool_calls': message.get('tool_calls', [])
            }

        except Exception as e:
            logger.error(f"[OLLAMA] Error: {e}", exc_info=True)
            return {
                'content': f'Error al comunicar con Ollama: {str(e)}',
                'tool_calls': []
            }

    def _call_openai_with_tools(self, messages: List[Dict]) -> Dict[str, Any]:
        """Llama a OpenAI con function calling."""
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

        try:
            # Convertir mensajes al formato LangChain
            lc_messages = []
            for msg in messages:
                role = msg.get('role')
                content = msg.get('content', '')

                if role == 'user':
                    lc_messages.append(HumanMessage(content=content))
                elif role == 'assistant':
                    tool_calls = msg.get('tool_calls', [])
                    if tool_calls:
                        formatted_tool_calls = []
                        for tc in tool_calls:
                            func = tc.get('function', {})
                            tc_id = tc.get('id', f"call_{func.get('name')}_{id(tc)}")
                            formatted_tool_calls.append({
                                "name": func.get('name'),
                                "args": func.get('arguments', {}),
                                "id": tc_id
                            })
                        lc_messages.append(AIMessage(content=content, tool_calls=formatted_tool_calls))
                    else:
                        lc_messages.append(AIMessage(content=content))
                elif role == 'tool':
                    tool_call_id = msg.get('tool_call_id', 'default')
                    lc_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))

            # Obtener tools en formato OpenAI
            tools = self.tool_registry.get_openai_tools()

            # Bind tools al LLM
            llm_with_tools = self.llm.bind_tools(tools)

            # Log request
            if self.chat_logger:
                messages_for_log = []
                for msg in lc_messages:
                    if hasattr(msg, 'content'):
                        messages_for_log.append({
                            'role': getattr(msg, 'type', 'unknown'),
                            'content': msg.content
                        })

                self.chat_logger.log_llm_request(
                    provider=self.llm_provider,
                    model=self.llm_model,
                    messages=messages_for_log,
                    tools=tools,
                    context="AGENT"
                )

            # Llamar al LLM
            response = llm_with_tools.invoke(lc_messages)

            # Log response
            if self.chat_logger:
                self.chat_logger.log_llm_response(response, context="AGENT")

            # Extraer tool calls si existen
            tool_calls = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append({
                        'id': tc.get('id', f"call_{tc.get('name')}_{id(tc)}"),
                        'function': {
                            'name': tc.get('name'),
                            'arguments': tc.get('args', {})
                        }
                    })

            return {
                'content': response.content if hasattr(response, 'content') else '',
                'tool_calls': tool_calls
            }

        except Exception as e:
            logger.error(f"[OPENAI] Error: {e}", exc_info=True)
            return {
                'content': f'Error al comunicar con OpenAI: {str(e)}',
                'tool_calls': []
            }

    def _call_gemini_with_tools(self, messages: List[Dict]) -> Dict[str, Any]:
        """Llama a Gemini con function calling."""
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

        try:
            # Convertir mensajes al formato LangChain
            lc_messages = []
            for msg in messages:
                role = msg.get('role')
                content = msg.get('content', '')

                if role == 'user':
                    lc_messages.append(HumanMessage(content=content))
                elif role == 'assistant':
                    tool_calls = msg.get('tool_calls', [])
                    if tool_calls:
                        formatted_tool_calls = []
                        for tc in tool_calls:
                            func = tc.get('function', {})
                            tc_id = tc.get('id', f"call_{func.get('name')}_{id(tc)}")
                            formatted_tool_calls.append({
                                "name": func.get('name'),
                                "args": func.get('arguments', {}),
                                "id": tc_id
                            })
                        lc_messages.append(AIMessage(content=content, tool_calls=formatted_tool_calls))
                    else:
                        lc_messages.append(AIMessage(content=content))
                elif role == 'tool':
                    tool_call_id = msg.get('tool_call_id', 'default')
                    lc_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))

            # Obtener tools en formato Gemini
            tools = self.tool_registry.get_gemini_tools()

            # Bind tools al LLM
            llm_with_tools = self.llm.bind_tools(tools)

            # Log request
            if self.chat_logger:
                messages_for_log = []
                for msg in lc_messages:
                    if hasattr(msg, 'content'):
                        messages_for_log.append({
                            'role': getattr(msg, 'type', 'unknown'),
                            'content': msg.content
                        })

                self.chat_logger.log_llm_request(
                    provider=self.llm_provider,
                    model=self.llm_model,
                    messages=messages_for_log,
                    tools=tools,
                    context="AGENT"
                )

            # Llamar al LLM
            response = llm_with_tools.invoke(lc_messages)

            # Log response
            if self.chat_logger:
                self.chat_logger.log_llm_response(response, context="AGENT")

            # Extraer tool calls si existen
            tool_calls = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append({
                        'id': tc.get('id', f"call_{tc.get('name')}_{id(tc)}"),
                        'function': {
                            'name': tc.get('name'),
                            'arguments': tc.get('args', {})
                        }
                    })

            return {
                'content': response.content if hasattr(response, 'content') else '',
                'tool_calls': tool_calls
            }

        except Exception as e:
            logger.error(f"[GEMINI] Error: {e}", exc_info=True)
            return {
                'content': f'Error al comunicar con Gemini: {str(e)}',
                'tool_calls': []
            }

    def _add_tool_results_to_messages(
        self,
        messages: List[Dict],
        llm_response: Dict,
        tool_calls: List[Dict],
        tool_results: List[Dict]
    ) -> List[Dict]:
        """Añade los resultados de las tools al historial de mensajes."""

        # Añadir mensaje del asistente con tool_calls
        messages.append({
            'role': 'assistant',
            'content': llm_response.get('content', ''),
            'tool_calls': tool_calls
        })

        # Añadir resultados de tools con tool_call_id
        for idx, result in enumerate(tool_results):
            tool_call_id = "default"
            if idx < len(tool_calls):
                tool_call_id = tool_calls[idx].get('id', f"call_{result.get('tool', 'unknown')}_{idx}")

            messages.append({
                'role': 'tool',
                'content': json.dumps(result, ensure_ascii=False),
                'tool_call_id': tool_call_id
            })

        return messages

    def _extract_failed_tools(self, tool_results_history: List[Dict]) -> List[Dict]:
        """Extrae información de las tools que fallaron."""
        failed_tools = []

        for tool_result in tool_results_history:
            tool_name = tool_result.get('tool', 'unknown')
            result_data = tool_result.get('result', {})

            if isinstance(result_data, dict):
                success = result_data.get('success', True)
                if not success:
                    error_msg = result_data.get('error', 'Error desconocido')
                    total_attempts = result_data.get('total_attempts', 1)
                    retries_exhausted = result_data.get('retries_exhausted', False)

                    failed_tools.append({
                        'name': tool_name,
                        'error': error_msg,
                        'retries': total_attempts - 1,
                        'total_attempts': total_attempts,
                        'retries_exhausted': retries_exhausted
                    })

                    logger.warning(f"[EXTRACT_FAILED] Tool '{tool_name}' falló: {error_msg}")

        return failed_tools

    def __repr__(self):
        return f"<FunctionCallingAgent(provider='{self.llm_provider}', model='{self.llm_model}', tools={len(self.tool_registry.tool_definitions)})>"
