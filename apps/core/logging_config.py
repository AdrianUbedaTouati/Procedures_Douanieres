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
    Logger para conversaciones de chat.
    Registra TODO lo que se envía y recibe del LLM, línea a línea, sin modificar.
    """

    def __init__(self, session_id: int, user_id: int):
        self.session_id = session_id
        self.user_id = user_id
        self.log_file = CHAT_LOGS_DIR / f"session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        # Crear logger específico para esta sesión
        self.logger = logging.getLogger(f'chat.session_{session_id}')
        self.logger.setLevel(logging.DEBUG)

        # Evitar duplicación de handlers
        if not self.logger.handlers:
            # Handler para archivo
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)

            # Formato: timestamp | nivel | mensaje (sin microsegundos para evitar error)
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

    def log_user_message(self, message: str):
        """Registra el mensaje del usuario"""
        self.logger.info("=" * 80)
        self.logger.info(f"USER MESSAGE (session {self.session_id})")
        self.logger.info("=" * 80)
        self.logger.info(message)

    def log_llm_request(self, provider: str, model: str, messages: list, tools: Optional[list] = None):
        """Registra la petición completa al LLM"""
        self.logger.info("=" * 80)
        self.logger.info(f"LLM REQUEST → {provider}/{model}")
        self.logger.info("=" * 80)

        # Registrar mensajes línea a línea
        self.logger.info("MESSAGES:")
        for idx, msg in enumerate(messages):
            self.logger.info(f"  [{idx}] Role: {msg.get('role', 'unknown')}")
            content = msg.get('content', '')
            if isinstance(content, str):
                for line in content.split('\n'):
                    self.logger.info(f"      {line}")
            else:
                self.logger.info(f"      {json.dumps(content, ensure_ascii=False, indent=2)}")

        # Registrar tools si existen
        if tools:
            self.logger.info("\nTOOLS AVAILABLE:")
            for idx, tool in enumerate(tools):
                self.logger.info(f"  [{idx}] {tool.get('name', 'unknown')}")
                if 'description' in tool:
                    self.logger.info(f"      Description: {tool['description']}")

    def log_llm_response(self, response: Any):
        """Registra la respuesta completa del LLM (sin modificar)"""
        self.logger.info("=" * 80)
        self.logger.info("LLM RESPONSE ←")
        self.logger.info("=" * 80)

        # Intentar serializar la respuesta completa
        try:
            if hasattr(response, 'model_dump'):
                # Pydantic model
                response_dict = response.model_dump()
            elif hasattr(response, '__dict__'):
                # Objeto con atributos
                response_dict = response.__dict__
            else:
                # Otro tipo
                response_dict = {'raw': str(response)}

            # Registrar línea a línea
            response_json = json.dumps(response_dict, ensure_ascii=False, indent=2)
            for line in response_json.split('\n'):
                self.logger.info(line)

        except Exception as e:
            self.logger.error(f"Error al serializar respuesta: {e}")
            self.logger.info(str(response))

    def log_tool_call(self, tool_name: str, tool_input: Dict[str, Any], iteration: int = None):
        """Registra una llamada a una tool con número de iteración"""
        self.logger.info("-" * 80)
        if iteration is not None:
            self.logger.info(f"TOOL CALL: {tool_name} (Iteration {iteration})")
        else:
            self.logger.info(f"TOOL CALL: {tool_name}")
        self.logger.info("-" * 80)
        self.logger.info("INPUT PARAMETERS:")
        input_json = json.dumps(tool_input, ensure_ascii=False, indent=2)
        for line in input_json.split('\n'):
            self.logger.info(f"  {line}")

    def log_tool_result(self, tool_name: str, result: Any, iteration: int = None, success: bool = True):
        """Registra el resultado de una tool con estado de éxito"""
        self.logger.info("-" * 80)
        status = "✓ SUCCESS" if success else "✗ FAILED"
        if iteration is not None:
            self.logger.info(f"TOOL RESULT: {tool_name} [{status}] (Iteration {iteration})")
        else:
            self.logger.info(f"TOOL RESULT: {tool_name} [{status}]")
        self.logger.info("-" * 80)
        try:
            if isinstance(result, dict):
                result_json = json.dumps(result, ensure_ascii=False, indent=2)
            else:
                result_json = str(result)

            for line in result_json.split('\n'):
                self.logger.info(f"  {line}")
        except Exception as e:
            self.logger.error(f"Error al serializar resultado: {e}")
            self.logger.info(f"  {str(result)}")

    def log_execution_flow(self, iteration: int, decision: str, tools_called: list):
        """Registra el flujo de ejecución de una iteración"""
        self.logger.info("=" * 80)
        self.logger.info(f"ITERATION {iteration} - EXECUTION FLOW")
        self.logger.info("=" * 80)
        self.logger.info(f"LLM Decision: {decision}")
        if tools_called:
            self.logger.info(f"Tools Called: {', '.join(tools_called)}")
        else:
            self.logger.info("Tools Called: None (generating final response)")

    def log_tool_execution_summary(self, tools_history: list):
        """Registra un resumen completo de todas las tools ejecutadas"""
        self.logger.info("=" * 80)
        self.logger.info("TOOL EXECUTION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Total tools executed: {len(tools_history)}")

        if not tools_history:
            self.logger.info("No tools were called during this query.")
            return

        # Agrupar por tool
        tool_counts = {}
        for tool_entry in tools_history:
            tool_name = tool_entry.get('tool', 'unknown')
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        self.logger.info("\nTool usage breakdown:")
        for tool_name, count in tool_counts.items():
            self.logger.info(f"  - {tool_name}: {count}x")

        self.logger.info("\nDetailed execution sequence:")
        for idx, tool_entry in enumerate(tools_history, 1):
            tool_name = tool_entry.get('tool', 'unknown')
            tool_args = tool_entry.get('arguments', {})
            tool_result = tool_entry.get('result', {})
            success = tool_result.get('success', False) if isinstance(tool_result, dict) else True
            status = "✓" if success else "✗"

            self.logger.info(f"\n  {idx}. {status} {tool_name}")

            # Mostrar parámetros
            if tool_args:
                self.logger.info(f"     Parameters:")
                args_json = json.dumps(tool_args, ensure_ascii=False, indent=6)
                for line in args_json.split('\n'):
                    self.logger.info(f"     {line}")

            # Mostrar resumen del resultado
            if isinstance(tool_result, dict):
                self.logger.info(f"     Result:")

                # Campos clave del resultado
                if 'success' in tool_result:
                    self.logger.info(f"       - success: {tool_result.get('success')}")
                if 'count' in tool_result:
                    self.logger.info(f"       - count: {tool_result.get('count')}")
                if 'message' in tool_result:
                    self.logger.info(f"       - message: {tool_result.get('message')}")
                if 'error' in tool_result:
                    self.logger.info(f"       - error: {tool_result.get('error')}")

                # Para find_best_tender: mostrar ID del documento encontrado
                if 'result' in tool_result and isinstance(tool_result['result'], dict):
                    doc_id = tool_result['result'].get('id')
                    if doc_id:
                        self.logger.info(f"       - document_id: {doc_id}")

                # Para find_top_tenders: mostrar IDs de documentos encontrados
                if 'results' in tool_result and isinstance(tool_result['results'], list):
                    doc_ids = [r.get('id', 'unknown') for r in tool_result['results']]
                    self.logger.info(f"       - document_ids: {doc_ids}")

        self.logger.info("\n" + "=" * 80)

    def log_assistant_message(self, message: str, metadata: Optional[Dict] = None):
        """Registra el mensaje final del asistente"""
        self.logger.info("=" * 80)
        self.logger.info("ASSISTANT MESSAGE")
        self.logger.info("=" * 80)
        self.logger.info(message)

        if metadata:
            self.logger.info("\nMETADATA:")
            metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)
            for line in metadata_json.split('\n'):
                self.logger.info(f"  {line}")

    def log_error(self, error: Exception, context: str = ""):
        """Registra un error"""
        self.logger.error("=" * 80)
        self.logger.error(f"ERROR: {context}")
        self.logger.error("=" * 80)
        self.logger.error(f"Type: {type(error).__name__}")
        self.logger.error(f"Message: {str(error)}")
        self.logger.exception(error)


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
