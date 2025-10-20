# -*- coding: utf-8 -*-
"""
Agente con Function Calling para Ollama, OpenAI y Google Gemini.
Versión 2.0 del sistema RAG con tools dinámicas.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import sys
import logging
import json

# Importar tools
sys.path.append(str(Path(__file__).parent))
from tools.registry import ToolRegistry

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
        retriever,
        db_session=None,
        max_iterations: int = 5,
        temperature: float = 0.3,
        company_context: str = "",
        tenders_summary: str = ""
    ):
        """
        Inicializa el agente con function calling.

        Args:
            llm_provider: Proveedor ("ollama", "openai", "google")
            llm_model: Modelo específico
            llm_api_key: API key (no necesaria para Ollama)
            retriever: Retriever de ChromaDB
            db_session: Sesión de base de datos Django
            max_iterations: Máximo de iteraciones del loop
            temperature: Temperatura del LLM
            company_context: Contexto de la empresa del usuario (opcional)
            tenders_summary: Resumen de licitaciones disponibles (opcional)
        """
        self.llm_provider = llm_provider.lower()
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.company_context = company_context  # Guardar contexto de empresa
        self.tenders_summary = tenders_summary  # Guardar resumen de licitaciones

        # Validaciones
        if self.llm_provider not in ['ollama', 'openai', 'google']:
            raise ValueError(f"Proveedor '{llm_provider}' no soportado. Use: ollama, openai, google")

        if self.llm_provider != 'ollama' and not llm_api_key:
            raise ValueError(f"API key requerida para {llm_provider}")

        # Inicializar LLM
        logger.info(f"[AGENT] Inicializando {llm_provider} - {llm_model}")
        self.llm = self._create_llm()

        # Inicializar tool registry
        logger.info(f"[AGENT] Inicializando tool registry...")
        self.tool_registry = ToolRegistry(retriever, db_session)

        logger.info(f"[AGENT] Agente inicializado con {len(self.tool_registry.tools)} tools")

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

            # Remover prefijo "models/" si existe
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
                [{'role': 'user'/'assistant', 'content': '...'}, ...]

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

                # Extraer documentos usados de los tool results (para compatibilidad con Django)
                documents = self._extract_documents_from_tool_results(tool_results_history)

                return {
                    'answer': final_answer,
                    'tools_used': tools_used,
                    'tool_results': tool_results_history,
                    'iterations': iteration,
                    'documents': documents,  # Para compatibilidad con ChatAgentService
                    'route': 'function_calling',  # Para compatibilidad con ChatAgentService
                    'verified_fields': [],  # Para compatibilidad con ChatAgentService
                    'metadata': {
                        'provider': self.llm_provider,
                        'model': self.llm_model,
                        'max_iterations': self.max_iterations
                    }
                }

            # Ejecutar tool calls
            logger.info(f"[TOOLS] LLM solicitó {len(tool_calls)} tool(s)")
            results = self.tool_registry.execute_tool_calls(tool_calls)

            # Registrar tools usadas
            for result in results:
                tool_name = result.get('tool')
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

        # Extraer documentos usados de los tool results (para compatibilidad con Django)
        documents = self._extract_documents_from_tool_results(tool_results_history)

        return {
            'answer': 'Lo siento, no pude completar la tarea en el número de pasos permitidos. Intenta hacer la pregunta de otra manera o más específica.',
            'tools_used': tools_used,
            'tool_results': tool_results_history,
            'iterations': iteration,
            'documents': documents,  # Para compatibilidad con ChatAgentService
            'route': 'function_calling',  # Para compatibilidad con ChatAgentService
            'verified_fields': [],  # Para compatibilidad con ChatAgentService
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

        # Añadir system prompt para instruir al modelo a usar tools
        system_prompt_parts = [
            "Eres un asistente experto en licitaciones públicas europeas. Tienes acceso a herramientas especializadas para consultar información sobre licitaciones.",
            ""
        ]

        # Añadir resumen de licitaciones disponibles si existe
        if self.tenders_summary:
            system_prompt_parts.append("=" * 60)
            system_prompt_parts.append(self.tenders_summary)
            system_prompt_parts.append("=" * 60)
            system_prompt_parts.append("")
            system_prompt_parts.append("Usa este listado para tener una idea general de las licitaciones disponibles.")
            system_prompt_parts.append("Para consultas específicas, SIEMPRE usa las herramientas de búsqueda.")
            system_prompt_parts.append("")

        # Añadir contexto de empresa si existe
        if self.company_context:
            system_prompt_parts.append("=" * 60)
            system_prompt_parts.append("INFORMACIÓN DE LA EMPRESA DEL USUARIO:")
            system_prompt_parts.append("=" * 60)
            system_prompt_parts.append(self.company_context)
            system_prompt_parts.append("=" * 60)
            system_prompt_parts.append("")
            system_prompt_parts.append("Cuando el usuario pregunte sobre su empresa o pida información personalizada,")
            system_prompt_parts.append("usa esta información de contexto para responder de forma específica.")
            system_prompt_parts.append("")

        system_prompt_parts.extend([
            "IMPORTANTE: Debes SIEMPRE usar las herramientas disponibles para responder preguntas sobre licitaciones. NO inventes información.",
            "",
            "Herramientas disponibles:",
            "- search_tenders: Búsqueda general por contenido/tema",
            "- find_by_budget: Filtrar por presupuesto (úsala para \"más cara\", \"mayor presupuesto\", etc.)",
            "- find_by_deadline: Filtrar por fecha límite",
            "- find_by_cpv: Filtrar por código CPV",
            "- find_by_location: Filtrar por ubicación geográfica",
            "- get_tender_details: Obtener detalles completos de una licitación específica",
            "- get_statistics: Obtener estadísticas (úsala para \"¿cuál es la más cara?\", \"promedio\", etc.)",
            "- compare_tenders: Comparar múltiples licitaciones",
            "- get_tender_xml: Obtener XML original de una licitación",
            "",
            "Cuando el usuario pregunte por licitaciones, DEBES usar las herramientas apropiadas. Por ejemplo:",
            "- \"¿Cuál es la licitación más cara?\" → USA get_statistics",
            "- \"Licitaciones de software\" → USA search_tenders",
            "- \"Licitaciones entre 50k y 100k\" → USA find_by_budget"
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
        """
        Llama al LLM con las tools disponibles.

        Returns:
            Dict con 'content' y 'tool_calls'
        """
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
                    # Si tiene tool_calls, incluirlos
                    tool_calls = msg.get('tool_calls', [])
                    if tool_calls:
                        # OpenAI espera tool_calls en formato específico
                        formatted_tool_calls = []
                        for tc in tool_calls:
                            import json
                            func = tc.get('function', {})
                            formatted_tool_calls.append({
                                "name": func.get('name'),
                                "args": func.get('arguments', {}),
                                "id": f"call_{func.get('name')}_{id(tc)}"
                            })
                        lc_messages.append(AIMessage(content=content, tool_calls=formatted_tool_calls))
                    else:
                        lc_messages.append(AIMessage(content=content))
                elif role == 'tool':
                    # Resultado de tool
                    lc_messages.append(ToolMessage(content=content, tool_call_id="default"))

            # Obtener tools en formato OpenAI
            tools = self.tool_registry.get_openai_tools()

            # Bind tools al LLM
            llm_with_tools = self.llm.bind_tools(tools)

            # Llamar al LLM
            response = llm_with_tools.invoke(lc_messages)

            # Extraer tool calls si existen
            tool_calls = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append({
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
                    # Si tiene tool_calls, incluirlos
                    tool_calls = msg.get('tool_calls', [])
                    if tool_calls:
                        # Gemini espera tool_calls en formato específico
                        formatted_tool_calls = []
                        for tc in tool_calls:
                            func = tc.get('function', {})
                            formatted_tool_calls.append({
                                "name": func.get('name'),
                                "args": func.get('arguments', {}),
                                "id": f"call_{func.get('name')}_{id(tc)}"
                            })
                        lc_messages.append(AIMessage(content=content, tool_calls=formatted_tool_calls))
                    else:
                        lc_messages.append(AIMessage(content=content))
                elif role == 'tool':
                    # Resultado de tool
                    lc_messages.append(ToolMessage(content=content, tool_call_id="default"))

            # Obtener tools en formato Gemini
            tools = self.tool_registry.get_gemini_tools()

            # Bind tools al LLM
            llm_with_tools = self.llm.bind_tools(tools)

            # Llamar al LLM
            response = llm_with_tools.invoke(lc_messages)

            # Extraer tool calls si existen
            tool_calls = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append({
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

        # Añadir resultados de tools
        for result in tool_results:
            messages.append({
                'role': 'tool',
                'content': json.dumps(result, ensure_ascii=False)
            })

        return messages

    def _extract_documents_from_tool_results(self, tool_results_history: List[Dict]) -> List[Dict]:
        """
        Extrae información de documentos de los resultados de tools para compatibilidad con Django.

        Args:
            tool_results_history: Lista de resultados de tool calls

        Returns:
            Lista de diccionarios con formato compatible con ChatAgentService:
            [{'ojs_notice_id': '...', 'section': '...', 'content': '...'}, ...]
        """
        documents = []

        for tool_result in tool_results_history:
            tool_name = tool_result.get('tool', '')
            result_data = tool_result.get('result', {})

            # Si fue search_tenders, extraer documentos de los resultados
            if tool_name == 'search_tenders' and result_data.get('success'):
                for tender in result_data.get('results', []):
                    documents.append({
                        'ojs_notice_id': tender.get('id', 'unknown'),
                        'section': tender.get('section', 'unknown'),
                        'content': tender.get('preview', '')
                    })

            # Si fue get_tender_details, extraer el tender completo
            elif tool_name == 'get_tender_details' and result_data.get('success'):
                tender = result_data.get('tender', {})
                documents.append({
                    'ojs_notice_id': tender.get('id', 'unknown'),
                    'section': 'details',
                    'content': f"{tender.get('title', '')} - {tender.get('description', '')[:200]}"
                })

            # find_by_budget también devuelve licitaciones
            elif tool_name == 'find_by_budget' and result_data.get('success'):
                for tender in result_data.get('results', []):
                    documents.append({
                        'ojs_notice_id': tender.get('id', 'unknown'),
                        'section': 'budget_search',
                        'content': f"{tender.get('title', '')} - Budget: {tender.get('budget', 'N/A')}"
                    })

            # find_by_deadline también devuelve licitaciones
            elif tool_name == 'find_by_deadline' and result_data.get('success'):
                for tender in result_data.get('results', []):
                    documents.append({
                        'ojs_notice_id': tender.get('id', 'unknown'),
                        'section': 'deadline_search',
                        'content': f"{tender.get('title', '')} - Deadline: {tender.get('deadline_date', 'N/A')}"
                    })

            # find_by_cpv también devuelve licitaciones
            elif tool_name == 'find_by_cpv' and result_data.get('success'):
                for tender in result_data.get('results', []):
                    documents.append({
                        'ojs_notice_id': tender.get('id', 'unknown'),
                        'section': tender.get('section', 'cpv_search'),
                        'content': tender.get('preview', '')
                    })

            # get_tender_xml devuelve XML
            elif tool_name == 'get_tender_xml' and result_data.get('success'):
                documents.append({
                    'ojs_notice_id': result_data.get('tender_id', 'unknown'),
                    'section': 'xml',
                    'content': f"XML content ({result_data.get('xml_length', 0)} chars)"
                })

            # find_by_location también devuelve licitaciones
            elif tool_name == 'find_by_location' and result_data.get('success'):
                for tender in result_data.get('results', []):
                    documents.append({
                        'ojs_notice_id': tender.get('id', 'unknown'),
                        'section': tender.get('section', 'location_search'),
                        'content': tender.get('preview', '')
                    })

            # compare_tenders devuelve comparación
            elif tool_name == 'compare_tenders' and result_data.get('success'):
                comparison = result_data.get('comparison', {})
                for tender in comparison.get('tenders', []):
                    documents.append({
                        'ojs_notice_id': tender.get('id', 'unknown'),
                        'section': 'comparison',
                        'content': f"{tender.get('title', '')} - {tender.get('buyer', '')}"
                    })

            # get_statistics no devuelve documentos específicos, solo estadísticas

        return documents

    def __repr__(self):
        return f"<FunctionCallingAgent(provider='{self.llm_provider}', model='{self.llm_model}', tools={len(self.tool_registry.tools)})>"
