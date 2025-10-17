# -*- coding: utf-8 -*-
"""
Agente LangGraph para RAG sobre licitaciones eForms.
Implementa el patrón Agentic RAG con nodos: route → retrieve → grade → verify → answer.
"""

from __future__ import annotations
from typing import List, Dict, Any, Literal
from typing_extensions import TypedDict
from pathlib import Path
import sys
import logging

# LangGraph y LangChain imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document

# Importar módulos propios
sys.path.append(str(Path(__file__).parent))
import config  # Import module instead of specific values to allow dynamic updates
from config import LLM_PROVIDER, LLM_MODEL, LLM_TEMPERATURE
from retriever import create_retriever
from prompts import (
    SYSTEM_PROMPT, create_answer_prompt, create_grading_prompt,
    create_routing_prompt, NO_CONTEXT_MESSAGE
)
from tools_xml import XmlLookupTool

# Importar todos los LLMs (lazy import)
# Esto permite que el agente pueda cambiar entre proveedores dinámicamente
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_nvidia_ai_endpoints import ChatNVIDIA
except ImportError:
    ChatNVIDIA = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

# Determinar LLM_CLASS por defecto según configuración
if LLM_PROVIDER == "google":
    LLM_CLASS = ChatGoogleGenerativeAI
elif LLM_PROVIDER == "nvidia":
    LLM_CLASS = ChatNVIDIA
else:  # openai
    LLM_CLASS = ChatOpenAI

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ESTADO DEL GRAFO
# ============================================================================

class AgentState(TypedDict):
    """
    Estado del agente RAG.
    Maneja el flujo de mensajes y documentos a través del grafo.
    """
    question: str  # Pregunta original del usuario
    messages: List[HumanMessage | AIMessage | SystemMessage]  # Historial de mensajes
    documents: List[Document]  # Documentos recuperados
    relevant_documents: List[Document]  # Documentos relevantes tras grading
    answer: str  # Respuesta final
    route: str  # Ruta decidida (vectorstore/specific_lookup/general)
    verified_fields: List[Dict[str, Any]]  # Campos verificados con XmlLookup
    iteration: int  # Contador de iteraciones


# ============================================================================
# AGENTE RAG
# ============================================================================

class EFormsRAGAgent:
    """
    Agente RAG para consultas sobre licitaciones eForms.
    Implementa el patrón Agentic RAG con LangGraph.
    """

    def __init__(
        self,
        api_key: str,
        llm_provider: str,
        llm_model: str = None,
        temperature: float = None,
        k_retrieve: int = 6,
        use_grading: bool = True,
        use_verification: bool = True
    ):
        """
        Inicializa el agente.

        Args:
            api_key: API key del usuario (REQUERIDO)
            llm_provider: Proveedor de LLM ("google", "nvidia", "openai") (REQUERIDO)
            llm_model: Modelo de LLM
            temperature: Temperatura del LLM
            k_retrieve: Número de documentos a recuperar
            use_grading: Activar nodo de grading
            use_verification: Activar nodo de verificación
        """
        if not api_key:
            raise ValueError("API key es requerida. Configura tu API key en tu perfil de usuario.")
        if not llm_provider:
            raise ValueError("llm_provider es requerido ('google', 'nvidia', 'openai')")

        self.api_key = api_key
        self.llm_provider = llm_provider
        self.llm_model = llm_model or LLM_MODEL
        self.temperature = temperature if temperature is not None else LLM_TEMPERATURE
        self.k_retrieve = k_retrieve
        self.use_grading = use_grading
        self.use_verification = use_verification

        # Inicializar LLM
        logger.info(f"Inicializando LLM: {self.llm_provider} - {self.llm_model}")
        logger.info(f"Using API Key: {self.api_key[:20]}...")

        if self.llm_provider == "google":
            # Para Gemini, usar el nombre sin el prefijo "models/"
            model_name = self.llm_model.replace("models/", "") if self.llm_model.startswith("models/") else self.llm_model
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=self.temperature,
                google_api_key=self.api_key
            )
        elif self.llm_provider == "nvidia":
            self.llm = ChatNVIDIA(
                model=self.llm_model,
                temperature=self.temperature,
                nvidia_api_key=self.api_key
            )
        else:  # openai
            self.llm = ChatOpenAI(
                model=self.llm_model,
                temperature=self.temperature,
                openai_api_key=self.api_key
            )

        # Inicializar retriever y tools con el mismo proveedor y API key
        embedding_model = None
        if self.llm_provider == "google":
            embedding_model = "models/embedding-001"
        elif self.llm_provider == "nvidia":
            embedding_model = "nvidia/nv-embedqa-e5-v5"
        elif self.llm_provider == "openai":
            embedding_model = "text-embedding-3-small"

        logger.info(f"Creating retriever with provider={self.llm_provider}, embedding_model={embedding_model}")
        self.retriever = create_retriever(
            k=self.k_retrieve,
            provider=self.llm_provider,
            api_key=self.api_key,
            embedding_model=embedding_model
        )
        self.xml_lookup = XmlLookupTool()

        # Construir grafo
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Construye el grafo del agente."""
        workflow = StateGraph(AgentState)

        # Añadir nodos
        workflow.add_node("route", self._route_node)
        workflow.add_node("retrieve", self._retrieve_node)

        if self.use_grading:
            workflow.add_node("grade", self._grade_node)

        if self.use_verification:
            workflow.add_node("verify", self._verify_node)

        workflow.add_node("answer", self._answer_node)

        # Definir punto de entrada
        workflow.set_entry_point("route")

        # Transiciones desde route
        workflow.add_conditional_edges(
            "route",
            self._decide_after_route,
            {
                "retrieve": "retrieve",
                "answer": "answer"  # Para consultas generales
            }
        )

        # Transiciones desde retrieve
        if self.use_grading:
            workflow.add_edge("retrieve", "grade")
            # Transiciones desde grade
            workflow.add_conditional_edges(
                "grade",
                self._decide_after_grade,
                {
                    "verify": "verify" if self.use_verification else "answer",
                    "answer": "answer",
                    "retrieve": "retrieve"  # Re-intentar con query reescrita
                }
            )
        else:
            if self.use_verification:
                workflow.add_edge("retrieve", "verify")
            else:
                workflow.add_edge("retrieve", "answer")

        # Transiciones desde verify
        if self.use_verification:
            workflow.add_edge("verify", "answer")

        # Transiciones desde answer
        workflow.add_edge("answer", END)

        # Compilar grafo
        return workflow.compile()

    # ========================================================================
    # NODOS DEL GRAFO
    # ========================================================================

    def _route_node(self, state: AgentState) -> AgentState:
        """
        Nodo de routing: clasifica la consulta.
        """
        question = state["question"]
        logger.info(f"[ROUTE] Clasificando consulta: {question}")

        # Por ahora, siempre rutear a vectorstore
        # En el futuro, usar el LLM para clasificar
        state["route"] = "vectorstore"
        state["iteration"] = state.get("iteration", 0) + 1

        logger.info(f"[ROUTE] Ruta decidida: {state['route']}")
        return state

    def _retrieve_node(self, state: AgentState) -> AgentState:
        """
        Nodo de recuperación: busca documentos relevantes.
        """
        question = state["question"]
        logger.info(f"[RETRIEVE] Buscando documentos para: {question}")

        # Recuperar documentos
        documents = self.retriever.retrieve(question, k=self.k_retrieve)

        state["documents"] = documents

        # Si no se usa grading, marcar todos los documentos como relevantes
        if not self.use_grading:
            state["relevant_documents"] = documents

        logger.info(f"[RETRIEVE] Recuperados {len(documents)} documentos")

        return state

    def _grade_node(self, state: AgentState) -> AgentState:
        """
        Nodo de grading: evalúa relevancia de documentos.
        """
        question = state["question"]
        documents = state["documents"]

        logger.info(f"[GRADE] Evaluando {len(documents)} documentos")

        relevant_docs = []
        for doc in documents:
            # Crear prompt de grading
            grade_prompt = create_grading_prompt(question, doc)

            # Evaluar relevancia (simplificado - en producción usar structured output)
            try:
                response = self.llm.invoke([HumanMessage(content=grade_prompt)])
                grade = response.content.strip().lower()

                if "yes" in grade or "sí" in grade:
                    relevant_docs.append(doc)
                    logger.debug(f"[GRADE] Documento relevante: {doc.metadata.get('chunk_id')}")
                else:
                    logger.debug(f"[GRADE] Documento no relevante: {doc.metadata.get('chunk_id')}")

            except Exception as e:
                logger.error(f"[GRADE] Error evaluando documento: {e}")
                # En caso de error, considerar relevante por seguridad
                relevant_docs.append(doc)

        state["relevant_documents"] = relevant_docs
        logger.info(f"[GRADE] {len(relevant_docs)}/{len(documents)} documentos relevantes")

        return state

    def _verify_node(self, state: AgentState) -> AgentState:
        """
        Nodo de verificación: verifica campos críticos con XmlLookup.
        """
        relevant_docs = state.get("relevant_documents", state["documents"])

        logger.info(f"[VERIFY] Verificando campos críticos")

        verified_fields = []

        # Buscar campos críticos en los documentos
        for doc in relevant_docs:
            metadata = doc.metadata
            source_path = metadata.get("source_path")

            if not source_path:
                continue

            # Verificar presupuesto
            if "budget" in doc.metadata.get("section", ""):
                budget_info = self.xml_lookup.lookup_budget(source_path)
                if budget_info:
                    verified_fields.append({
                        "name": "presupuesto",
                        "value": f"{budget_info['budget_eur']} {budget_info['currency']}",
                        "source": source_path,
                        "xpath": budget_info['xpath']
                    })

            # Verificar deadline
            if "deadline" in doc.metadata.get("section", ""):
                deadline_info = self.xml_lookup.lookup_deadline(source_path)
                if deadline_info:
                    verified_fields.append({
                        "name": "deadline",
                        "value": f"{deadline_info['tender_deadline_date']} {deadline_info.get('tender_deadline_time', '')}",
                        "source": source_path,
                        "xpath": deadline_info['xpath_date']
                    })

        state["verified_fields"] = verified_fields
        logger.info(f"[VERIFY] Verificados {len(verified_fields)} campos")

        return state

    def _answer_node(self, state: AgentState) -> AgentState:
        """
        Nodo de respuesta: genera la respuesta final.
        """
        question = state["question"]
        relevant_docs = state.get("relevant_documents", state.get("documents", []))

        logger.info(f"[ANSWER] Generando respuesta")

        if not relevant_docs:
            state["answer"] = NO_CONTEXT_MESSAGE
            logger.warning("[ANSWER] Sin documentos relevantes")
            return state

        # Crear prompt de respuesta
        answer_prompt = create_answer_prompt(question, relevant_docs)

        # Generar respuesta
        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=answer_prompt)
            ]

            response = self.llm.invoke(messages)
            state["answer"] = response.content

            logger.info(f"[ANSWER] Respuesta generada ({len(response.content)} caracteres)")

        except Exception as e:
            logger.error(f"[ANSWER] Error generando respuesta: {e}")
            state["answer"] = "Lo siento, hubo un error generando la respuesta. Por favor, intenta de nuevo."

        return state

    # ========================================================================
    # FUNCIONES DE DECISIÓN (Edges condicionales)
    # ========================================================================

    def _decide_after_route(self, state: AgentState) -> Literal["retrieve", "answer"]:
        """Decide qué hacer después del routing."""
        route = state.get("route", "vectorstore")

        if route == "general":
            return "answer"
        else:
            return "retrieve"

    def _decide_after_grade(self, state: AgentState) -> Literal["verify", "answer", "retrieve"]:
        """Decide qué hacer después del grading."""
        relevant_docs = state.get("relevant_documents", [])
        iteration = state.get("iteration", 1)

        # Si no hay documentos relevantes y es la primera iteración, reintentar
        if not relevant_docs and iteration < 2:
            logger.info("[DECIDE] Sin documentos relevantes, reintentando...")
            return "retrieve"

        # Si hay pocos documentos y es primera iteración, reintentar
        if len(relevant_docs) < 2 and iteration < 2:
            logger.info("[DECIDE] Pocos documentos relevantes, reintentando...")
            return "retrieve"

        # Si hay documentos relevantes, continuar
        if self.use_verification:
            return "verify"
        else:
            return "answer"

    # ========================================================================
    # MÉTODO PRINCIPAL
    # ========================================================================

    def query(self, question: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Ejecuta una consulta en el agente.

        Args:
            question: Pregunta del usuario
            filters: Filtros estructurados opcionales

        Returns:
            Diccionario con respuesta y metadatos
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"CONSULTA: {question}")
        logger.info(f"{'='*60}\n")

        # Estado inicial
        initial_state = {
            "question": question,
            "messages": [],
            "documents": [],
            "relevant_documents": [],
            "answer": "",
            "route": "",
            "verified_fields": [],
            "iteration": 0
        }

        # Ejecutar grafo
        try:
            final_state = self.graph.invoke(initial_state)

            # Preparar respuesta
            result = {
                "question": question,
                "answer": final_state["answer"],
                "documents": [
                    {
                        "ojs_notice_id": doc.metadata.get("ojs_notice_id"),
                        "section": doc.metadata.get("section"),
                        "source_path": doc.metadata.get("source_path"),
                        "content": doc.page_content[:200] + "..."
                    }
                    for doc in final_state.get("relevant_documents", final_state.get("documents", []))
                ],
                "verified_fields": final_state.get("verified_fields", []),
                "route": final_state.get("route"),
                "iterations": final_state.get("iteration", 0)
            }

            logger.info(f"\n{'='*60}")
            logger.info(f"RESPUESTA GENERADA")
            logger.info(f"{'='*60}\n")

            return result

        except Exception as e:
            logger.error(f"Error ejecutando grafo: {e}")
            import traceback
            traceback.print_exc()
            return {
                "question": question,
                "answer": "Lo siento, hubo un error procesando tu consulta.",
                "documents": [],
                "verified_fields": [],
                "error": str(e)
            }


# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================

def create_agent(
    k_retrieve: int = 6,
    use_grading: bool = True,
    use_verification: bool = True
) -> EFormsRAGAgent:
    """
    Crea una instancia del agente RAG.

    Args:
        k_retrieve: Número de documentos a recuperar
        use_grading: Activar grading de relevancia
        use_verification: Activar verificación con XmlLookup

    Returns:
        Instancia del agente
    """
    return EFormsRAGAgent(
        k_retrieve=k_retrieve,
        use_grading=use_grading,
        use_verification=use_verification
    )


if __name__ == "__main__":
    # Prueba del agente
    print("\n=== PRUEBA DEL AGENTE RAG ===\n")

    # Crear agente
    agent = create_agent(k_retrieve=5, use_grading=False, use_verification=True)

    # Consulta de prueba
    question = "¿Cuál es el presupuesto de los servicios de SAP?"

    result = agent.query(question)

    print(f"\nPregunta: {result['question']}")
    print(f"\nRespuesta:\n{result['answer']}")
    print(f"\nDocumentos usados: {len(result['documents'])}")
    for i, doc in enumerate(result['documents'][:3], 1):
        print(f"  {i}. [{doc['section']}] {doc['ojs_notice_id']}")
    print(f"\nCampos verificados: {len(result['verified_fields'])}")
    for field in result['verified_fields']:
        print(f"  - {field['name']}: {field['value']}")
