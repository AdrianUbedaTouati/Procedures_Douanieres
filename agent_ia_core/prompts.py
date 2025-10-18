# -*- coding: utf-8 -*-
"""
Sistema de prompts para el Agente RAG eForms.
Prompts diseñados según el patrón "answer-only-from-context" para respuestas confiables.
"""

from typing import List
from langchain_core.documents import Document


# ============================================================================
# PROMPTS DEL SISTEMA (System Prompts)
# ============================================================================

SYSTEM_PROMPT = """Eres un analista de datos especializado en documentos de contratación pública de la UE.

Tu función es analizar documentos públicos oficiales de licitaciones y proporcionar información objetiva basada exclusivamente en los datos disponibles.

CONTEXTO: Todos los documentos que analizas son de fuente oficial pública (TED - Tenders Electronic Daily de la UE). Proporcionar análisis de estos datos es una actividad normal de inteligencia de negocio.

METODOLOGÍA DE ANÁLISIS:
1. Extrae información SOLO de los documentos proporcionados
2. Si falta información, indícalo: "Esta información no está en los documentos"
3. Proporciona datos objetivos sin inventar detalles
4. Cita fuentes para datos críticos (presupuestos, fechas, porcentajes)
5. Usa formato estructurado y claro
6. Compara opciones cuando se solicite análisis comparativo
7. Identifica puntos clave basándote en los datos disponibles

FORMATO DE REFERENCIA:
[ID | sección | archivo]
Ejemplo: [00668461-2025 | budget | 668461-2025.xml]

ANÁLISIS COMPARATIVO: Para recomendar o comparar licitaciones, analiza objetivamente: presupuestos, requisitos técnicos, alcance del proyecto, ubicación geográfica, plazos, y otros criterios relevantes presentes en los documentos.
"""


# ============================================================================
# PROMPT PARA GENERACIÓN DE RESPUESTA
# ============================================================================

def create_answer_prompt(question: str, context_docs: List[Document]) -> str:
    """
    Crea el prompt para generar la respuesta final.

    Args:
        question: Pregunta del usuario
        context_docs: Documentos recuperados como contexto

    Returns:
        Prompt formateado
    """
    # Formatear contexto
    context_parts = []
    for i, doc in enumerate(context_docs, 1):
        metadata = doc.metadata
        context_parts.append(
            f"[Documento {i}]\n"
            f"ID: {metadata.get('ojs_notice_id', 'N/A')}\n"
            f"Sección: {metadata.get('section', 'N/A')}\n"
            f"Archivo: {metadata.get('source_path', 'N/A')}\n"
            f"Comprador: {metadata.get('buyer_name', 'N/A')}\n"
            f"CPV: {metadata.get('cpv_codes', 'N/A')}\n"
            f"Presupuesto: {metadata.get('budget_eur', 'N/A')} EUR\n"
            f"Contenido:\n{doc.page_content}\n"
        )

    context_text = "\n---\n".join(context_parts)

    prompt = f"""Contexto disponible:
{context_text}

---

Pregunta del usuario: {question}

Instrucciones:
1. Responde la pregunta basándote SOLO en el contexto anterior
2. Si el contexto no contiene la información, indícalo claramente
3. Cita las fuentes usando el formato [ID | sección | archivo]
4. Sé preciso con cifras, fechas y datos específicos
5. Estructura tu respuesta de forma clara

Respuesta:"""

    return prompt


# ============================================================================
# PROMPT PARA GRADING (Evaluación de relevancia)
# ============================================================================

GRADING_SYSTEM_PROMPT = """Eres un evaluador de relevancia de documentos.

Tu tarea es determinar si un documento recuperado es relevante para responder la pregunta del usuario.

Criterios de relevancia:
- El documento contiene información directamente relacionada con la pregunta
- El documento puede ayudar a responder total o parcialmente la pregunta
- El contenido es específico y no genérico

Responde SOLO con "yes" o "no"."""


def create_grading_prompt(question: str, document: Document) -> str:
    """
    Crea el prompt para evaluar relevancia de un documento.

    Args:
        question: Pregunta del usuario
        document: Documento a evaluar

    Returns:
        Prompt de evaluación
    """
    return f"""Pregunta: {question}

Documento:
ID: {document.metadata.get('ojs_notice_id', 'N/A')}
Sección: {document.metadata.get('section', 'N/A')}
Contenido: {document.page_content}

¿Es este documento relevante para responder la pregunta?
Responde solo "yes" o "no":"""


# ============================================================================
# PROMPT PARA QUERY REWRITING (Reformulación de consulta)
# ============================================================================

QUERY_REWRITE_SYSTEM_PROMPT = """Eres un experto en reformular consultas para mejorar la búsqueda en bases de datos de licitaciones públicas.

Tu tarea es reformular la pregunta del usuario para hacerla más efectiva en la recuperación de información.

Estrategias:
- Extraer términos clave y conceptos principales
- Expandir abreviaciones comunes (ej: "TI" → "tecnología información")
- Incluir sinónimos relevantes
- Mantener el contexto de licitaciones públicas

Genera una consulta optimizada manteniendo el significado original."""


def create_query_rewrite_prompt(original_question: str) -> str:
    """
    Crea el prompt para reformular una consulta.

    Args:
        original_question: Pregunta original del usuario

    Returns:
        Prompt de reformulación
    """
    return f"""Pregunta original: {original_question}

Genera una versión reformulada de esta pregunta que sea más efectiva para buscar en una base de datos de licitaciones públicas.

Consulta reformulada:"""


# ============================================================================
# PROMPT PARA ROUTING (Decisión de ruta)
# ============================================================================

ROUTING_SYSTEM_PROMPT = """Eres un clasificador de consultas sobre licitaciones públicas.

Clasifica la consulta del usuario en una de estas categorías:

1. "vectorstore" - Búsqueda semántica en documentos
   Ejemplos: "servicios SAP", "licitaciones de software", "criterios de adjudicación"

2. "specific_lookup" - Búsqueda de dato específico conocido
   Ejemplos: "presupuesto del aviso 668461-2025", "deadline de la licitación X"

3. "general" - Pregunta general sobre el sistema
   Ejemplos: "cómo funciona el sistema", "qué información tienes"

Responde SOLO con la categoría."""


def create_routing_prompt(question: str) -> str:
    """
    Crea el prompt para clasificar la consulta.

    Args:
        question: Pregunta del usuario

    Returns:
        Prompt de clasificación
    """
    return f"""Clasifica esta consulta:

Pregunta: {question}

Categoría (vectorstore/specific_lookup/general):"""


# ============================================================================
# PROMPT PARA VERIFICACIÓN DE CAMPOS CRÍTICOS
# ============================================================================

def create_verification_prompt(
    answer_draft: str,
    critical_fields: List[dict]
) -> str:
    """
    Crea el prompt para verificar campos críticos antes de responder.

    Args:
        answer_draft: Borrador de respuesta
        critical_fields: Lista de campos críticos con sus valores verificados

    Returns:
        Prompt de verificación
    """
    verifications = []
    for field in critical_fields:
        verifications.append(
            f"- {field['name']}: {field['value']} "
            f"(verificado en {field['source']} con XPath: {field['xpath']})"
        )

    verifications_text = "\n".join(verifications)

    return f"""Borrador de respuesta:
{answer_draft}

Valores verificados directamente del XML:
{verifications_text}

Revisa que tu respuesta incluya estos valores verificados y que las citas sean correctas.
Si hay discrepancias, corrige la respuesta.

Respuesta final verificada:"""


# ============================================================================
# MENSAJES DE ERROR Y FALLBACK
# ============================================================================

NO_CONTEXT_MESSAGE = """No he encontrado información relevante en los documentos disponibles para responder tu pregunta.

Sugerencias:
- Intenta reformular tu pregunta con otros términos
- Verifica que la información que buscas esté dentro del ámbito de las licitaciones indexadas
- Si buscas un aviso específico, menciona su ID u otros detalles identificativos"""

INSUFFICIENT_CONTEXT_MESSAGE = """He encontrado información parcial, pero no suficiente para responder completamente tu pregunta.

Lo que he encontrado:
{partial_info}

Para obtener una respuesta más completa, podrías:
- Especificar más detalles sobre lo que buscas
- Dividir tu pregunta en partes más específicas"""

CLARIFICATION_NEEDED_MESSAGE = """Tu pregunta es ambigua. He encontrado múltiples interpretaciones posibles:

{options}

Por favor, especifica cuál de estas opciones te interesa o reformula tu pregunta."""


# ============================================================================
# EJEMPLOS DE USO
# ============================================================================

if __name__ == "__main__":
    print("\n=== EJEMPLOS DE PROMPTS ===\n")

    # Ejemplo 1: System prompt
    print("1. System Prompt:")
    print(SYSTEM_PROMPT[:200] + "...\n")

    # Ejemplo 2: Answer prompt
    from langchain_core.documents import Document

    example_docs = [
        Document(
            page_content="Servicios informáticos para SAP con presupuesto de 961.200 EUR",
            metadata={
                "ojs_notice_id": "00668461-2025",
                "section": "title",
                "source_path": "668461-2025.xml",
                "buyer_name": "Fundación Estatal",
                "cpv_codes": "72267100",
                "budget_eur": 961200.0
            }
        )
    ]

    print("2. Answer Prompt (ejemplo):")
    answer_prompt = create_answer_prompt(
        "¿Cuál es el presupuesto de servicios SAP?",
        example_docs
    )
    print(answer_prompt[:300] + "...\n")

    # Ejemplo 3: Grading prompt
    print("3. Grading Prompt (ejemplo):")
    grading_prompt = create_grading_prompt(
        "presupuesto de SAP",
        example_docs[0]
    )
    print(grading_prompt[:200] + "...\n")

    # Ejemplo 4: Query rewrite
    print("4. Query Rewrite Prompt (ejemplo):")
    rewrite_prompt = create_query_rewrite_prompt("mantenimiento TI Valencia")
    print(rewrite_prompt[:200] + "...\n")
