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
from datetime import datetime

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


def get_current_datetime() -> str:
    """
    Devuelve la fecha y hora actual en formato legible para el LLM.

    Returns:
        String con formato: "Fecha actual: YYYY-MM-DD | Hora: HH:MM:SS"
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
        retriever,
        db_session=None,
        user=None,
        max_iterations: int = 5,
        temperature: float = 0.3,
        company_context: str = "",
        tenders_summary: str = "",
        chat_logger=None
    ):
        """
        Inicializa el agente con function calling.

        Args:
            llm_provider: Proveedor ("ollama", "openai", "google")
            llm_model: Modelo específico
            llm_api_key: API key (no necesaria para Ollama)
            retriever: Retriever de ChromaDB
            db_session: Sesión de base de datos Django
            user: Usuario de Django para tools de contexto
            max_iterations: Máximo de iteraciones del loop
            temperature: Temperatura del LLM
            company_context: (DEPRECATED) Ahora se usa get_company_info tool
            tenders_summary: (DEPRECATED) Ahora se usa get_tenders_summary tool
            chat_logger: ChatLogger instance para logging detallado (opcional)
        """
        self.llm_provider = llm_provider.lower()
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.user = user
        self.chat_logger = chat_logger
        # Mantener por compatibilidad pero ya no se usan
        self.company_context = company_context
        self.tenders_summary = tenders_summary

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
        self.tool_registry = ToolRegistry(retriever, db_session, user=user)

        # Inicializar grading tool con el LLM (si el usuario la activó)
        if user and getattr(user, 'use_grading', False):
            self.tool_registry.initialize_grading_tool(self.llm)

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

        # Determinar si es el primer mensaje
        is_first_message = not conversation_history or len(conversation_history) == 0

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

            # LOG: Flujo de ejecución con las tools que se van a llamar
            if self.chat_logger:
                tools_to_call = [tc.get('function', {}).get('name', 'unknown') for tc in tool_calls]
                self.chat_logger.log_execution_flow(iteration, f"Call {len(tool_calls)} tool(s)", tools_to_call)

            results = self.tool_registry.execute_tool_calls(tool_calls)

            # Registrar tools usadas y LOG cada una
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

        # Determinar si es el primer mensaje (sin historial)
        is_first_message = not conversation_history or len(conversation_history) == 0

        # System prompt base (siempre presente)
        system_prompt_parts = [
            "Eres un asistente experto en licitaciones públicas europeas. Tienes acceso a herramientas especializadas para consultar información sobre licitaciones.",
            "",
            f"CONTEXTO TEMPORAL: {get_current_datetime()}",
            ""
        ]

        # Instrucción para usar tools de contexto
        if self.user:
            system_prompt_parts.extend([
                "INFORMACIÓN IMPORTANTE:",
                "- Tienes acceso a la herramienta 'get_company_info' para obtener información sobre la empresa del usuario.",
                "- Tienes acceso a la herramienta 'get_tenders_summary' para obtener un resumen de las licitaciones disponibles.",
                "- Usa 'get_company_info' cuando el usuario pregunte sobre su empresa o necesites información para recomendaciones personalizadas.",
                "- Usa 'get_tenders_summary' solo cuando el usuario explícitamente pregunte qué licitaciones hay disponibles o pida un resumen general.",
                ""
            ])

        # Instrucciones (siempre presentes)
        system_prompt_parts.extend([
            "IMPORTANTE: Tienes a disposicion herramientas disponibles para responder preguntas. NO inventes información.",
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
        ])

        # Añadir web_search y browse_webpage si están disponibles
        if 'web_search' in self.tool_registry.tools:
            system_prompt_parts.extend([
                "- web_search: Buscar información en internet (clima, noticias, precios, datos actuales)",
                "- browse_webpage: Navegar a una URL específica para extraer contenido detallado",
            ])

        system_prompt_parts.extend([
            "",
            "Cuando el usuario pregunte por licitaciones, puedes usar las herramientas apropiadas. Por ejemplo:",
            "- \"¿Cuál es la licitación más cara?\" → USA get_statistics",
            "- \"Licitaciones de software\" → USA search_tenders",
            "- \"Licitaciones entre 50k y 100k\" → USA find_by_budget",
        ])

        # Instrucciones para web_search
        if 'web_search' in self.tool_registry.tools:
            system_prompt_parts.extend([
                "- \"¿Qué tiempo hace en París?\" → USA web_search",
                "- \"Precio del Bitcoin\" → USA web_search",
                "- \"Noticias recientes sobre...\" → USA web_search",
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
                            # Usar el ID que ya viene en el tool_call, no generar uno nuevo
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
                    # Resultado de tool
                    tool_call_id = msg.get('tool_call_id', 'default')
                    lc_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))

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
                        'id': tc.get('id', f"call_{tc.get('name')}_{id(tc)}"),  # Guardar ID del tool call
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
                            # Usar el ID que ya viene en el tool_call, no generar uno nuevo
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
                    # Resultado de tool
                    tool_call_id = msg.get('tool_call_id', 'default')
                    lc_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))

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
                        'id': tc.get('id', f"call_{tc.get('name')}_{id(tc)}"),  # Guardar ID del tool call
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
            # Obtener tool_call_id del tool_call correspondiente
            tool_call_id = "default"
            if idx < len(tool_calls):
                tool_call_id = tool_calls[idx].get('id', f"call_{result.get('tool', 'unknown')}_{idx}")

            messages.append({
                'role': 'tool',
                'content': json.dumps(result, ensure_ascii=False),
                'tool_call_id': tool_call_id  # Añadir ID real del tool call
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
        logger.info(f"[EXTRACT_DOCS] Procesando {len(tool_results_history)} tool results")
        logger.info(f"[EXTRACT_DOCS] Tools llamadas: {[tr.get('tool') for tr in tool_results_history]}")

        for tool_result in tool_results_history:
            tool_name = tool_result.get('tool', '')
            result_data = tool_result.get('result', {})

            # find_best_tender devuelve UN documento (result singular)
            if tool_name == 'find_best_tender' and result_data.get('success'):
                tender = result_data.get('result')
                if tender:  # result puede ser None si no hay resultados
                    doc_entry = {
                        'ojs_notice_id': tender.get('id', 'unknown'),
                        'section': ', '.join(tender.get('sections_found', ['unknown'])),
                        'content': tender.get('preview', '')
                    }
                    logger.info(f"[EXTRACT_DOCS] find_best_tender: Añadiendo documento {doc_entry['ojs_notice_id']} con sections: {doc_entry['section']}")
                    documents.append(doc_entry)

            # find_top_tenders devuelve MÚLTIPLES documentos (results plural)
            elif tool_name == 'find_top_tenders' and result_data.get('success'):
                for tender in result_data.get('results', []):
                    documents.append({
                        'ojs_notice_id': tender.get('id', 'unknown'),
                        'section': f"rank_{tender.get('rank', 0)}",
                        'content': tender.get('preview', '')
                    })

            # Si fue search_tenders (DEPRECATED), extraer documentos de los resultados
            elif tool_name == 'search_tenders' and result_data.get('success'):
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

        logger.info(f"[EXTRACT_DOCS] Total documentos extraídos: {len(documents)}")
        for idx, doc in enumerate(documents):
            logger.info(f"[EXTRACT_DOCS] Doc {idx+1}: ID={doc.get('ojs_notice_id')}, section={doc.get('section')}")

        return documents

    def __repr__(self):
        return f"<FunctionCallingAgent(provider='{self.llm_provider}', model='{self.llm_model}', tools={len(self.tool_registry.tools)})>"
