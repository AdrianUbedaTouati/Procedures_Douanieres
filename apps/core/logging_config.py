"""
Sistema de logging detallado y transparente para TenderAI Platform.

Este módulo proporciona loggers especializados para diferentes componentes:
- Chat: Conversaciones completas (input/output LLM)
- Indexación: Proceso de indexación de XMLs
- Obtención: Descarga de licitaciones
"""

import logging
import os
from pathlib import Path
from datetime import datetime
import json
from typing import Any, Dict, Optional


# Directorio base de logs (raíz del proyecto)
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Subdirectorios
CHAT_LOGS_DIR = LOGS_DIR / 'chat'
INDEXACION_LOGS_DIR = LOGS_DIR / 'indexacion'
OBTENER_LOGS_DIR = LOGS_DIR / 'obtener'

for directory in [CHAT_LOGS_DIR, INDEXACION_LOGS_DIR, OBTENER_LOGS_DIR]:
    directory.mkdir(exist_ok=True)


class ChatLogger:
    """
    Sistema de doble logging para conversaciones de chat.

    Genera 2 archivos por sesión:
    1. SIMPLIFICADO (*_simple.log): Trazas importantes (funciones, parámetros, resultados resumidos)
    2. DETALLADO (*_detailed.log): TODO sin excepción (prompts completos, respuestas raw, metadatos)
    """

    def __init__(self, session_id: int, user_id: int):
        self.session_id = session_id
        self.user_id = user_id

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f"session_{session_id}_{timestamp}"

        # Archivos de log
        self.simple_log_file = CHAT_LOGS_DIR / f"{base_name}_simple.log"
        self.detailed_log_file = CHAT_LOGS_DIR / f"{base_name}_detailed.log"

        # Logger SIMPLIFICADO: Información importante, concisa
        self.logger_simple = logging.getLogger(f'chat.session_{session_id}.simple')
        self.logger_simple.setLevel(logging.INFO)
        self.logger_simple.propagate = False  # No propagar a root logger

        # Logger DETALLADO: TODO sin filtrar
        self.logger_detailed = logging.getLogger(f'chat.session_{session_id}.detailed')
        self.logger_detailed.setLevel(logging.DEBUG)
        self.logger_detailed.propagate = False

        # Configurar handlers si no existen
        if not self.logger_simple.handlers:
            # Handler simple
            simple_handler = logging.FileHandler(self.simple_log_file, encoding='utf-8')
            simple_handler.setLevel(logging.INFO)
            simple_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            simple_handler.setFormatter(simple_formatter)
            self.logger_simple.addHandler(simple_handler)

        if not self.logger_detailed.handlers:
            # Handler detallado
            detailed_handler = logging.FileHandler(self.detailed_log_file, encoding='utf-8')
            detailed_handler.setLevel(logging.DEBUG)
            detailed_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            detailed_handler.setFormatter(detailed_formatter)
            self.logger_detailed.addHandler(detailed_handler)

        # Log inicial
        self._log_session_start()

    def _log_session_start(self):
        """Registra inicio de sesión en ambos logs"""
        # Simple
        self.logger_simple.info("=" * 80)
        self.logger_simple.info(f"NUEVA SESIÓN DE CHAT - ID: {self.session_id} | Usuario: {self.user_id}")
        self.logger_simple.info("=" * 80)

        # Detallado
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info(f"NUEVA SESIÓN DE CHAT (DETAILED LOG)")
        self.logger_detailed.info(f"Session ID: {self.session_id}")
        self.logger_detailed.info(f"User ID: {self.user_id}")
        self.logger_detailed.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger_detailed.info(f"Log files:")
        self.logger_detailed.info(f"  - Simple: {self.simple_log_file.name}")
        self.logger_detailed.info(f"  - Detailed: {self.detailed_log_file.name}")
        self.logger_detailed.info("=" * 80)

    def log_user_message(self, message: str):
        """Registra el mensaje del usuario"""
        # Simple: solo el mensaje
        self.logger_simple.info("=" * 80)
        self.logger_simple.info(f"👤 USER MESSAGE")
        self.logger_simple.info("=" * 80)
        self.logger_simple.info(message)

        # Detallado: igual pero con más contexto
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info(f"👤 USER MESSAGE (session {self.session_id})")
        self.logger_detailed.info(f"Length: {len(message)} characters")
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info(message)

    def log_llm_request(self, provider: str, model: str, messages: list, tools: Optional[list] = None, context: str = "AGENT"):
        """
        Registra la petición completa al LLM.

        Args:
            provider: Proveedor del LLM (ollama, openai, etc.)
            model: Modelo utilizado
            messages: Lista de mensajes enviados
            tools: Lista de tools disponibles (opcional)
            context: Contexto de la llamada (AGENT, REVIEWER, IMPROVEMENT, etc.)
        """
        # SIMPLE: Resumen conciso
        self.logger_simple.info("=" * 80)
        self.logger_simple.info(f"🤖 LLM REQUEST [{context}] → {provider}/{model}")
        self.logger_simple.info("=" * 80)
        self.logger_simple.info(f"Messages count: {len(messages)}")

        # Resumen de roles
        role_summary = {}
        for msg in messages:
            role = msg.get('role', 'unknown')
            role_summary[role] = role_summary.get(role, 0) + 1
        self.logger_simple.info(f"Message roles: {dict(role_summary)}")

        # Solo último mensaje del user (si existe)
        user_messages = [m for m in messages if m.get('role') == 'user']
        if user_messages:
            last_user_msg = user_messages[-1].get('content', '')
            preview = last_user_msg[:200] + '...' if len(last_user_msg) > 200 else last_user_msg
            self.logger_simple.info(f"Last user message preview: {preview}")

        if tools:
            self.logger_simple.info(f"Tools available: {len(tools)} tools")
            tool_names = [t.get('name', 'unknown') for t in tools[:5]]
            self.logger_simple.info(f"Tool names (first 5): {', '.join(tool_names)}")

        # DETALLADO: TODO sin filtrar
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info(f"🤖 LLM REQUEST [{context}] → {provider}/{model}")
        self.logger_detailed.info("=" * 80)

        # Registrar TODOS los mensajes completos
        self.logger_detailed.info(f"MESSAGES ({len(messages)} total):")
        for idx, msg in enumerate(messages):
            self.logger_detailed.info(f"  [{idx}] Role: {msg.get('role', 'unknown')}")
            content = msg.get('content', '')
            if isinstance(content, str):
                # Loguear línea a línea
                for line in content.split('\n'):
                    self.logger_detailed.info(f"      {line}")
            else:
                # Serializar como JSON
                self.logger_detailed.info(f"      {json.dumps(content, ensure_ascii=False, indent=2)}")

        # Registrar TODAS las tools con descripciones completas
        if tools:
            self.logger_detailed.info(f"\nTOOLS AVAILABLE ({len(tools)} total):")
            for idx, tool in enumerate(tools):
                self.logger_detailed.info(f"  [{idx}] {tool.get('name', 'unknown')}")
                if 'description' in tool:
                    self.logger_detailed.info(f"      Description: {tool['description']}")
                if 'parameters' in tool:
                    params_json = json.dumps(tool['parameters'], ensure_ascii=False, indent=6)
                    self.logger_detailed.info(f"      Parameters:")
                    for line in params_json.split('\n'):
                        self.logger_detailed.info(f"      {line}")

    def log_llm_response(self, response: Any, context: str = "AGENT"):
        """
        Registra la respuesta completa del LLM.

        Args:
            response: Respuesta del LLM (puede ser objeto Pydantic, dict, etc.)
            context: Contexto de la llamada (AGENT, REVIEWER, IMPROVEMENT, etc.)
        """
        # Serializar respuesta
        try:
            if hasattr(response, 'model_dump'):
                response_dict = response.model_dump()
            elif hasattr(response, '__dict__'):
                response_dict = response.__dict__
            else:
                response_dict = {'raw': str(response)}
        except Exception as e:
            response_dict = {'error_serializing': str(e), 'raw': str(response)}

        # SIMPLE: Resumen de la respuesta
        self.logger_simple.info("=" * 80)
        self.logger_simple.info(f"✅ LLM RESPONSE [{context}] ←")
        self.logger_simple.info("=" * 80)

        # Extraer información clave
        content = response_dict.get('content', '')
        if isinstance(content, str):
            preview = content[:300] + '...' if len(content) > 300 else content
            self.logger_simple.info(f"Content preview: {preview}")
            self.logger_simple.info(f"Content length: {len(content)} characters")
        else:
            self.logger_simple.info(f"Content type: {type(content).__name__}")

        # Tool calls si existen
        tool_calls = response_dict.get('additional_kwargs', {}).get('tool_calls', [])
        if tool_calls:
            self.logger_simple.info(f"Tool calls: {len(tool_calls)}")
            for tc in tool_calls:
                func_name = tc.get('function', {}).get('name', 'unknown')
                self.logger_simple.info(f"  - {func_name}")

        # Tokens si existen
        response_metadata = response_dict.get('response_metadata', {})
        if 'total_tokens' in response_metadata:
            self.logger_simple.info(f"Tokens: {response_metadata.get('total_tokens')} "
                                   f"(in: {response_metadata.get('input_tokens', 0)}, "
                                   f"out: {response_metadata.get('output_tokens', 0)})")

        # DETALLADO: Respuesta COMPLETA
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info(f"✅ LLM RESPONSE [{context}] ←")
        self.logger_detailed.info("=" * 80)

        # Serializar y registrar TODO
        response_json = json.dumps(response_dict, ensure_ascii=False, indent=2, default=str)
        for line in response_json.split('\n'):
            self.logger_detailed.info(line)

    def log_tool_call(self, tool_name: str, tool_input: Dict[str, Any], iteration: int = None):
        """Registra una llamada a una tool con número de iteración"""
        iter_text = f" (Iteration {iteration})" if iteration else ""

        # SIMPLE: Solo nombre y parámetros clave
        self.logger_simple.info("-" * 80)
        self.logger_simple.info(f"🔧 TOOL CALL: {tool_name}{iter_text}")
        self.logger_simple.info("-" * 80)
        # Mostrar solo parámetros resumidos
        param_summary = {k: (v if len(str(v)) < 50 else f"{str(v)[:50]}...") for k, v in tool_input.items()}
        self.logger_simple.info(f"Parameters: {param_summary}")

        # DETALLADO: TODO
        self.logger_detailed.info("-" * 80)
        self.logger_detailed.info(f"🔧 TOOL CALL: {tool_name}{iter_text}")
        self.logger_detailed.info("-" * 80)
        self.logger_detailed.info("INPUT PARAMETERS:")
        input_json = json.dumps(tool_input, ensure_ascii=False, indent=2, default=str)
        for line in input_json.split('\n'):
            self.logger_detailed.info(f"  {line}")

    def log_tool_result(self, tool_name: str, result: Any, iteration: int = None, success: bool = True):
        """Registra el resultado de una tool con estado de éxito"""
        status = "✓ SUCCESS" if success else "✗ FAILED"
        iter_text = f" (Iteration {iteration})" if iteration else ""

        # SIMPLE: Resultado resumido
        self.logger_simple.info("-" * 80)
        self.logger_simple.info(f"✅ TOOL RESULT: {tool_name} [{status}]{iter_text}")
        self.logger_simple.info("-" * 80)

        if isinstance(result, dict):
            # Campos clave para simple
            key_fields = {}
            if 'success' in result:
                key_fields['success'] = result['success']
            if 'count' in result:
                key_fields['count'] = result['count']
            if 'message' in result:
                msg = result['message']
                key_fields['message'] = msg if len(msg) < 100 else f"{msg[:100]}..."
            if 'error' in result:
                key_fields['error'] = result['error']
            if 'total_attempts' in result and result.get('total_attempts', 1) > 1:
                key_fields['retries'] = result['total_attempts'] - 1

            self.logger_simple.info(f"Key fields: {key_fields}")
        else:
            self.logger_simple.info(f"Result: {str(result)[:200]}")

        # DETALLADO: Resultado COMPLETO
        self.logger_detailed.info("-" * 80)
        self.logger_detailed.info(f"✅ TOOL RESULT: {tool_name} [{status}]{iter_text}")
        self.logger_detailed.info("-" * 80)

        try:
            if isinstance(result, dict):
                result_json = json.dumps(result, ensure_ascii=False, indent=2, default=str)
            else:
                result_json = str(result)

            for line in result_json.split('\n'):
                self.logger_detailed.info(f"  {line}")
        except Exception as e:
            self.logger_detailed.error(f"Error al serializar resultado: {e}")
            self.logger_detailed.info(f"  {str(result)}")

    def log_execution_flow(self, iteration: int, decision: str, tools_called: list):
        """Registra el flujo de ejecución de una iteración"""
        # SIMPLE
        self.logger_simple.info("=" * 80)
        self.logger_simple.info(f"🔄 ITERATION {iteration} - EXECUTION FLOW")
        self.logger_simple.info("=" * 80)
        self.logger_simple.info(f"Decision: {decision}")
        if tools_called:
            self.logger_simple.info(f"Tools: {', '.join(tools_called)}")
        else:
            self.logger_simple.info("Tools: None (final response)")

        # DETALLADO
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info(f"🔄 ITERATION {iteration} - EXECUTION FLOW")
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info(f"LLM Decision: {decision}")
        if tools_called:
            self.logger_detailed.info(f"Tools Called: {', '.join(tools_called)}")
        else:
            self.logger_detailed.info("Tools Called: None (generating final response)")

    def log_tool_execution_summary(self, tools_history: list):
        """Registra un resumen completo de todas las tools ejecutadas"""

        # SIMPLE: Resumen muy conciso
        self.logger_simple.info("=" * 80)
        self.logger_simple.info("📊 TOOL EXECUTION SUMMARY")
        self.logger_simple.info("=" * 80)
        self.logger_simple.info(f"Total tools executed: {len(tools_history)}")

        if not tools_history:
            self.logger_simple.info("No tools were called during this query.")
        else:
            # Agrupar por tool
            tool_counts = {}
            success_count = 0
            failed_count = 0

            for tool_entry in tools_history:
                tool_name = tool_entry.get('tool', 'unknown')
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

                tool_result = tool_entry.get('result', {})
                if isinstance(tool_result, dict):
                    if tool_result.get('success', True):
                        success_count += 1
                    else:
                        failed_count += 1
                else:
                    success_count += 1

            self.logger_simple.info(f"Success: {success_count} | Failed: {failed_count}")
            self.logger_simple.info("\nTool usage breakdown:")
            for tool_name, count in tool_counts.items():
                self.logger_simple.info(f"  - {tool_name}: {count}x")

        # DETALLADO: TODO con detalles completos
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info("📊 TOOL EXECUTION SUMMARY (DETAILED)")
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info(f"Total tools executed: {len(tools_history)}")

        if not tools_history:
            self.logger_detailed.info("No tools were called during this query.")
            return

        # Agrupar por tool
        tool_counts = {}
        for tool_entry in tools_history:
            tool_name = tool_entry.get('tool', 'unknown')
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        self.logger_detailed.info("\nTool usage breakdown:")
        for tool_name, count in tool_counts.items():
            self.logger_detailed.info(f"  - {tool_name}: {count}x")

        self.logger_detailed.info("\nDetailed execution sequence:")
        for idx, tool_entry in enumerate(tools_history, 1):
            tool_name = tool_entry.get('tool', 'unknown')
            tool_args = tool_entry.get('arguments', {})
            tool_result = tool_entry.get('result', {})
            success = tool_result.get('success', False) if isinstance(tool_result, dict) else True
            status = "✓" if success else "✗"

            self.logger_detailed.info(f"\n  {idx}. {status} {tool_name}")

            # Mostrar parámetros COMPLETOS
            if tool_args:
                self.logger_detailed.info(f"     Parameters:")
                args_json = json.dumps(tool_args, ensure_ascii=False, indent=6, default=str)
                for line in args_json.split('\n'):
                    self.logger_detailed.info(f"     {line}")

            # Mostrar resultado COMPLETO
            if isinstance(tool_result, dict):
                self.logger_detailed.info(f"     Result:")

                # Información sobre reintentos (si hubo)
                if 'total_attempts' in tool_result:
                    attempts = tool_result.get('total_attempts')
                    if attempts > 1:
                        self.logger_detailed.info(f"       - total_attempts: {attempts} (reintentos: {attempts - 1})")
                        if tool_result.get('retries_exhausted'):
                            self.logger_detailed.info(f"       - retries_exhausted: True ⚠️")

                # Campos clave del resultado
                if 'success' in tool_result:
                    self.logger_detailed.info(f"       - success: {tool_result.get('success')}")
                if 'count' in tool_result:
                    self.logger_detailed.info(f"       - count: {tool_result.get('count')}")
                if 'message' in tool_result:
                    self.logger_detailed.info(f"       - message: {tool_result.get('message')}")
                if 'error' in tool_result:
                    self.logger_detailed.info(f"       - error: {tool_result.get('error')}")

                # Para find_best_tender: mostrar ID del documento encontrado
                if 'result' in tool_result and isinstance(tool_result['result'], dict):
                    doc_id = tool_result['result'].get('id')
                    if doc_id:
                        self.logger_detailed.info(f"       - document_id: {doc_id}")

                # Para find_top_tenders: mostrar IDs de documentos encontrados
                if 'results' in tool_result and isinstance(tool_result['results'], list):
                    doc_ids = [r.get('id', 'unknown') for r in tool_result['results']]
                    self.logger_detailed.info(f"       - document_ids: {doc_ids}")

        self.logger_detailed.info("\n" + "=" * 80)

    def log_assistant_message(self, message: str, metadata: Optional[Dict] = None):
        """Registra el mensaje final del asistente"""
        # SIMPLE: Mensaje y resumen de metadata
        self.logger_simple.info("=" * 80)
        self.logger_simple.info("🤖 ASSISTANT MESSAGE (FINAL)")
        self.logger_simple.info("=" * 80)
        preview = message[:500] + '...' if len(message) > 500 else message
        self.logger_simple.info(preview)

        if metadata:
            self.logger_simple.info("\nMETADATA SUMMARY:")
            if 'tools_used' in metadata:
                self.logger_simple.info(f"  - tools_used: {metadata['tools_used']}")
            if 'iterations' in metadata:
                self.logger_simple.info(f"  - iterations: {metadata['iterations']}")
            if 'review_tracking' in metadata:
                review = metadata['review_tracking']
                self.logger_simple.info(f"  - review_performed: {review.get('review_performed', False)}")
                self.logger_simple.info(f"  - review_loops: {review.get('loops_executed', 0)}/{review.get('max_loops', 0)}")
                self.logger_simple.info(f"  - final_score: {review.get('final_score', 'N/A')}")

        # DETALLADO: TODO
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info("🤖 ASSISTANT MESSAGE (FINAL)")
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info(message)

        if metadata:
            self.logger_detailed.info("\nMETADATA (COMPLETE):")
            metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2, default=str)
            for line in metadata_json.split('\n'):
                self.logger_detailed.info(f"  {line}")

    def log_error(self, error: Exception, context: str = ""):
        """Registra un error"""
        # Ambos logs reciben errores completos
        self.logger_simple.error("=" * 80)
        self.logger_simple.error(f"❌ ERROR: {context}")
        self.logger_simple.error("=" * 80)
        self.logger_simple.error(f"Type: {type(error).__name__}")
        self.logger_simple.error(f"Message: {str(error)}")

        self.logger_detailed.error("=" * 80)
        self.logger_detailed.error(f"❌ ERROR: {context}")
        self.logger_detailed.error("=" * 80)
        self.logger_detailed.error(f"Type: {type(error).__name__}")
        self.logger_detailed.error(f"Message: {str(error)}")
        self.logger_detailed.exception(error)  # Solo detailed tiene traceback completo

    # =========================================================================
    # MÉTODOS ESPECÍFICOS PARA EL REVISOR
    # =========================================================================

    def log_review_start(self, loop_num: int, max_loops: int):
        """Registra inicio de un loop de revisión"""
        # SIMPLE
        self.logger_simple.info("=" * 80)
        self.logger_simple.info(f"🔍 REVIEW LOOP {loop_num}/{max_loops} - START")
        self.logger_simple.info("=" * 80)

        # DETALLADO
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info(f"🔍 REVIEW LOOP {loop_num}/{max_loops} - START")
        self.logger_detailed.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger_detailed.info("=" * 80)

    def log_reviewer_prompt(self, prompt: str, user_question: str, conversation_history: list, metadata: Dict):
        """Registra el prompt completo enviado al LLM Revisor"""
        # SIMPLE: Solo resumen
        self.logger_simple.info("-" * 80)
        self.logger_simple.info("📝 REVIEWER PROMPT (Summary)")
        self.logger_simple.info("-" * 80)
        self.logger_simple.info(f"User question: {user_question[:100]}...")
        self.logger_simple.info(f"Conversation history: {len(conversation_history)} messages")
        self.logger_simple.info(f"Documents used: {len(metadata.get('documents_used', []))}")
        self.logger_simple.info(f"Tools used: {metadata.get('tools_used', [])}")
        self.logger_simple.info(f"Prompt length: {len(prompt)} characters")

        # DETALLADO: TODO
        self.logger_detailed.info("-" * 80)
        self.logger_detailed.info("📝 REVIEWER PROMPT (COMPLETE)")
        self.logger_detailed.info("-" * 80)
        self.logger_detailed.info(f"User question: {user_question}")
        self.logger_detailed.info(f"\nConversation history ({len(conversation_history)} messages):")
        for idx, msg in enumerate(conversation_history):
            self.logger_detailed.info(f"  [{idx}] {msg.get('role', 'unknown')}: {msg.get('content', '')[:150]}...")

        self.logger_detailed.info(f"\nMetadata:")
        metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2, default=str)
        for line in metadata_json.split('\n'):
            self.logger_detailed.info(f"  {line}")

        self.logger_detailed.info(f"\n{'='*80}")
        self.logger_detailed.info("FULL PROMPT TO REVIEWER LLM:")
        self.logger_detailed.info('='*80)
        for line in prompt.split('\n'):
            self.logger_detailed.info(line)

    def log_reviewer_response(self, raw_response: str, parsed_result: Dict):
        """Registra la respuesta del LLM Revisor (raw y parseada)"""
        # SIMPLE: Solo resultado parseado
        self.logger_simple.info("-" * 80)
        self.logger_simple.info("✅ REVIEWER RESPONSE")
        self.logger_simple.info("-" * 80)
        self.logger_simple.info(f"Status: {parsed_result.get('status', 'UNKNOWN')}")
        self.logger_simple.info(f"Score: {parsed_result.get('score', 0)}/100")
        self.logger_simple.info(f"Issues: {len(parsed_result.get('issues', []))}")
        self.logger_simple.info(f"Suggestions: {len(parsed_result.get('suggestions', []))}")
        self.logger_simple.info(f"Tool suggestions: {len(parsed_result.get('tool_suggestions', []))}")

        if parsed_result.get('feedback'):
            feedback_preview = parsed_result['feedback'][:200] + '...' if len(parsed_result['feedback']) > 200 else parsed_result['feedback']
            self.logger_simple.info(f"Feedback preview: {feedback_preview}")

        # DETALLADO: Raw response + parsed result COMPLETO
        self.logger_detailed.info("-" * 80)
        self.logger_detailed.info("✅ REVIEWER RESPONSE (RAW)")
        self.logger_detailed.info("-" * 80)
        for line in raw_response.split('\n'):
            self.logger_detailed.info(line)

        self.logger_detailed.info("\n" + "-" * 80)
        self.logger_detailed.info("✅ REVIEWER RESPONSE (PARSED)")
        self.logger_detailed.info("-" * 80)
        parsed_json = json.dumps(parsed_result, ensure_ascii=False, indent=2, default=str)
        for line in parsed_json.split('\n'):
            self.logger_detailed.info(line)

    def log_improvement_prompt(self, prompt: str, loop_num: int, review_result: Dict):
        """Registra el prompt de mejora enviado al agente principal"""
        # SIMPLE: Resumen
        self.logger_simple.info("-" * 80)
        self.logger_simple.info(f"🔄 IMPROVEMENT PROMPT (Loop {loop_num})")
        self.logger_simple.info("-" * 80)
        self.logger_simple.info(f"Review score: {review_result.get('score', 0)}/100")
        self.logger_simple.info(f"Issues to fix: {len(review_result.get('issues', []))}")
        self.logger_simple.info(f"Tools suggested: {len(review_result.get('tool_suggestions', []))}")
        self.logger_simple.info(f"Prompt length: {len(prompt)} characters")

        # DETALLADO: Prompt COMPLETO
        self.logger_detailed.info("-" * 80)
        self.logger_detailed.info(f"🔄 IMPROVEMENT PROMPT (Loop {loop_num}) - COMPLETE")
        self.logger_detailed.info("-" * 80)
        for line in prompt.split('\n'):
            self.logger_detailed.info(line)

    def log_review_end(self, loop_num: int, decision: str, reason: str):
        """Registra fin de un loop de revisión"""
        # SIMPLE
        self.logger_simple.info("=" * 80)
        self.logger_simple.info(f"🏁 REVIEW LOOP {loop_num} - END")
        self.logger_simple.info("=" * 80)
        self.logger_simple.info(f"Decision: {decision}")
        self.logger_simple.info(f"Reason: {reason}")

        # DETALLADO
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info(f"🏁 REVIEW LOOP {loop_num} - END")
        self.logger_detailed.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger_detailed.info("=" * 80)
        self.logger_detailed.info(f"Decision: {decision}")
        self.logger_detailed.info(f"Reason: {reason}")


class IndexacionLogger:
    """
    Logger para el proceso de indexación de XMLs.
    """

    def __init__(self):
        self.log_file = INDEXACION_LOGS_DIR / f"indexacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        self.logger = logging.getLogger('indexacion')
        self.logger.setLevel(logging.DEBUG)

        # Evitar duplicación de handlers
        if not self.logger.handlers:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)

            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

    def log_start(self, xml_file: str):
        """Inicia el log de indexación de un XML"""
        self.logger.info("=" * 80)
        self.logger.info(f"INDEXANDO: {xml_file}")
        self.logger.info("=" * 80)

    def log_parsing(self, fields_extracted: Dict[str, Any]):
        """Registra los campos extraídos del XML"""
        self.logger.info("CAMPOS EXTRAIDOS:")
        fields_json = json.dumps(fields_extracted, ensure_ascii=False, indent=2, default=str)
        for line in fields_json.split('\n'):
            self.logger.info(f"  {line}")

    def log_xpaths_used(self, xpaths: Dict[str, str]):
        """Registra los XPaths usados"""
        self.logger.info("\nXPATHS USADOS:")
        for field, xpath in xpaths.items():
            self.logger.info(f"  {field}: {xpath}")

    def log_db_save(self, tender_id: str, created: bool):
        """Registra el guardado en base de datos"""
        action = "CREADO" if created else "ACTUALIZADO"
        self.logger.info(f"\nDB: {action} tender {tender_id}")

    def log_vectorization(self, tender_id: str, chunks_count: int):
        """Registra la vectorización"""
        self.logger.info(f"VECTORIZACION: {chunks_count} chunks creados para {tender_id}")

    def log_success(self, tender_id: str):
        """Registra éxito"""
        self.logger.info(f"OK Indexación completada para {tender_id}")
        self.logger.info("=" * 80 + "\n")

    def log_error(self, xml_file: str, error: Exception):
        """Registra error"""
        self.logger.error(f"ERROR en {xml_file}")
        self.logger.error(f"  Type: {type(error).__name__}")
        self.logger.error(f"  Message: {str(error)}")
        self.logger.exception(error)
        self.logger.error("=" * 80 + "\n")


class ObtenerLogger:
    """
    Logger para el proceso de descarga de licitaciones.
    """

    def __init__(self):
        self.log_file = OBTENER_LOGS_DIR / f"descarga_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        self.logger = logging.getLogger('obtener')
        self.logger.setLevel(logging.DEBUG)

        # Evitar duplicación de handlers
        if not self.logger.handlers:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)

            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

    def log_start(self, search_query: str):
        """Inicia el log de descarga"""
        self.logger.info("=" * 80)
        self.logger.info(f"DESCARGA INICIADA")
        self.logger.info("=" * 80)
        self.logger.info(f"Query: {search_query}")

    def log_api_request(self, url: str, params: Dict):
        """Registra petición a API de TED"""
        self.logger.info("\nAPI REQUEST:")
        self.logger.info(f"  URL: {url}")
        self.logger.info("  PARAMS:")
        for key, value in params.items():
            self.logger.info(f"    {key}: {value}")

    def log_api_response(self, status_code: int, notice_count: int):
        """Registra respuesta de API"""
        self.logger.info(f"\nAPI RESPONSE:")
        self.logger.info(f"  Status: {status_code}")
        self.logger.info(f"  Notices encontradas: {notice_count}")

    def log_download(self, notice_id: str, success: bool, file_path: Optional[str] = None):
        """Registra descarga de un XML"""
        if success:
            self.logger.info(f"OK Descargado: {notice_id} -> {file_path}")
        else:
            self.logger.error(f"X FALLO: {notice_id}")

    def log_summary(self, total: int, downloaded: int, failed: int):
        """Registra resumen final"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("RESUMEN DE DESCARGA")
        self.logger.info("=" * 80)
        self.logger.info(f"Total encontradas: {total}")
        self.logger.info(f"Descargadas: {downloaded}")
        self.logger.info(f"Fallidas: {failed}")
        self.logger.info("=" * 80 + "\n")


# Exportar loggers
__all__ = ['ChatLogger', 'IndexacionLogger', 'ObtenerLogger']
