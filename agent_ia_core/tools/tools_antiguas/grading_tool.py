# -*- coding: utf-8 -*-
"""
Tool para evaluar relevancia de documentos (Grading).
Portado desde EFormsRAGAgent._grade_node().

Esta tool permite al LLM filtrar documentos irrelevantes antes de generar
una respuesta, mejorando la precisión y reduciendo alucinaciones.
"""

from typing import List, Dict, Any, Optional
from .base import BaseTool
from langchain_core.messages import HumanMessage
import logging

logger = logging.getLogger(__name__)


class GradeDocumentsTool(BaseTool):
    """
    Evalúa la relevancia de documentos recuperados.

    Esta tool usa un LLM para determinar si cada documento
    es relevante para responder la pregunta del usuario.

    Casos de uso:
    - Después de search_tenders, para filtrar resultados irrelevantes
    - Cuando hay muchos documentos y quieres solo los más relevantes
    - Para mejorar la precisión eliminando ruido

    Impacto en rendimiento:
    - Añade N llamadas al LLM (N = número de documentos)
    - Típicamente 3-6 documentos = 3-6 llamadas extra
    - Incremento de ~50-100% en tiempo de respuesta

    Ejemplo de uso:
        Usuario: "Licitaciones de software con más de 100k EUR"
        1. search_tenders → 10 resultados
        2. grade_documents → filtrar a 6 relevantes
        3. Responder con solo los 6 relevantes
    """

    def __init__(self, llm):
        """
        Inicializa la tool con un LLM para evaluación.

        Args:
            llm: Instancia del LLM (ChatOllama, ChatOpenAI, etc.)
        """
        self.llm = llm
        self.name = "grade_documents"
        self.description = (
            "Evalúa la relevancia de documentos recuperados para una pregunta. "
            "Úsala después de search_tenders para filtrar documentos irrelevantes. "
            "Retorna solo los documentos relevantes para mejorar la precisión de la respuesta."
        )

    def get_schema(self) -> Dict[str, Any]:
        """Retorna el schema OpenAI Function Calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Pregunta original del usuario"
                    },
                    "document_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de IDs de licitaciones a evaluar (ojs_notice_id)"
                    }
                },
                "required": ["question", "document_ids"]
            }
        }

    def run(self, question: str, document_ids: List[str]) -> Dict[str, Any]:
        """
        Evalúa relevancia de documentos.

        Para cada documento, pregunta al LLM:
        "¿Es este documento relevante para la pregunta?"

        Args:
            question: Pregunta del usuario
            document_ids: Lista de IDs de licitaciones a evaluar

        Returns:
            Dict con:
                - success: bool - Si la operación fue exitosa
                - relevant_documents: List[str] - IDs de docs relevantes
                - filtered_count: int - Cuántos se filtraron
                - total_evaluated: int - Total evaluados
                - details: List[Dict] - Detalles de cada evaluación
        """
        try:
            from apps.tenders.models import Tender
            from agent_ia_core.prompts.prompts import create_grading_prompt

            logger.info(f"[GRADING] Evaluando {len(document_ids)} documentos para: {question[:60]}...")

            relevant_ids = []
            details = []

            for tender_id in document_ids:
                # Obtener tender desde la BD
                tender = Tender.objects.filter(ojs_notice_id=tender_id).first()
                if not tender:
                    logger.warning(f"[GRADING] Tender {tender_id} no encontrado")
                    continue

                # Crear documento simulado para grading
                # Usamos título + descripción (truncada) para la evaluación
                doc_content = f"{tender.title}\n{tender.description[:500] if tender.description else ''}"
                doc_metadata = {
                    'ojs_notice_id': tender.ojs_notice_id,
                    'section': 'general',
                    'buyer_name': tender.buyer_name
                }

                # Simular Document object (estructura simple)
                class SimpleDoc:
                    def __init__(self, content, metadata):
                        self.page_content = content
                        self.metadata = metadata

                doc = SimpleDoc(doc_content, doc_metadata)

                # Crear prompt de grading usando función de prompts.py
                grade_prompt = create_grading_prompt(question, doc)

                # Evaluar con LLM
                response = self.llm.invoke([HumanMessage(content=grade_prompt)])
                grade = response.content.strip().lower()

                # Determinar relevancia (buscar "yes" o "sí" en la respuesta)
                is_relevant = "yes" in grade or "sí" in grade or "si" in grade

                if is_relevant:
                    relevant_ids.append(tender_id)
                    logger.debug(f"[GRADING] ✓ Relevante: {tender_id} - {tender.title[:50]}")
                else:
                    logger.debug(f"[GRADING] ✗ No relevante: {tender_id} - {tender.title[:50]}")

                details.append({
                    'document_id': tender_id,
                    'title': tender.title[:100],
                    'relevant': is_relevant,
                    'reason': grade[:100]  # Razón del LLM (truncada)
                })

            filtered_count = len(document_ids) - len(relevant_ids)
            logger.info(f"[GRADING] Resultado: {len(relevant_ids)}/{len(document_ids)} relevantes ({filtered_count} filtrados)")

            return {
                'success': True,
                'relevant_documents': relevant_ids,
                'filtered_count': filtered_count,
                'total_evaluated': len(document_ids),
                'details': details,
                'message': f"Evaluados {len(document_ids)} documentos, {len(relevant_ids)} son relevantes."
            }

        except Exception as e:
            logger.error(f"[GRADING] Error al evaluar documentos: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'relevant_documents': document_ids,  # Fallback: retornar todos
                'message': f"Error en grading, retornando todos los documentos: {str(e)}"
            }
