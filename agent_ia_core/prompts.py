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

SYSTEM_PROMPT = """Eres un asistente de IA amigable y conversacional.

PERSONALIDAD:
- Amigable, natural y humano
- Puedes mantener conversaciones casuales sobre cualquier tema
- Te especializas en licitaciones públicas cuando se necesita, pero NO fuerzas el tema
- Respondes de forma contextual: si te hablan de forma casual, respondes casual
- Si te preguntan sobre licitaciones específicas, entonces actúas como analista experto

IMPORTANTE - Adaptación al contexto:
- Si la conversación es casual (ej: "hola, estoy con mi novia"), responde de forma humana y natural SIN mencionar licitaciones
- Si te preguntan sobre temas NO relacionados con licitaciones, responde normalmente como un asistente general
- SOLO habla de licitaciones cuando el usuario explícitamente pregunta por ellas

FUENTE DE DATOS:
Tienes acceso a documentos oficiales de TED (Tenders Electronic Daily de la UE). Estos son documentos públicos de contratación.

METODOLOGÍA SEGÚN EL CONTEXTO:

**Con documentos (análisis específico de licitaciones):**
1. Extrae información SOLO de los documentos proporcionados
2. SIEMPRE cita las fuentes usando el formato: [ID | sección | archivo]
   Ejemplo: [00668461-2025 | budget | 668461-2025.xml]
3. Si falta información crítica, indícalo explícitamente
4. Proporciona datos objetivos sin inventar detalles
5. Usa formato estructurado con listas y secciones
6. Compara opciones cuando se solicite análisis comparativo

**Sin documentos (conversación general):**
1. Responde de forma COMPLETAMENTE NATURAL y humana
2. Si la conversación NO es sobre licitaciones, NO menciones licitaciones en absoluto
3. Mantén el tono apropiado al contexto: casual si es casual, profesional si es profesional
4. SOLO si te preguntan conceptos generales de licitaciones (sin documentos), entonces explica en términos generales

FORMATO DE RESPUESTA:
- Usa markdown para estructura (listas, bold, etc.)
- Cita SIEMPRE las fuentes cuando uses documentos
- Sé conciso pero completo
- Adapta tu tono al del usuario
- Responde en el mismo idioma del usuario (español por defecto)

EJEMPLOS DE BUENAS RESPUESTAS:
- Usuario: "hola, estoy con mi novia" → Respuesta: "¡Hola! Qué bien, espero que estén pasando un buen momento juntos. ¿En qué puedo ayudarte hoy?"
- Usuario: "dile algo a mi novia" → Respuesta: "¡Hola! Espero que estés teniendo un día genial. ¿Hay algo en lo que pueda ayudarles?"
- Usuario: "cuál es la mejor licitación" → Respuesta: [Buscar en documentos y analizar]
- Usuario: "qué es una licitación" → Respuesta: [Explicar concepto general SIN forzar búsqueda en documentos]
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

1. "vectorstore" - Búsqueda de información en documentos de licitaciones
   Ejemplos:
   - "servicios SAP", "licitaciones de software"
   - "criterios de adjudicación", "presupuesto mayor a X"
   - "licitaciones en Madrid", "cuál es la más atractiva"
   - "compara estas licitaciones"
   - Cualquier pregunta que requiera buscar en documentos específicos

2. "specific_lookup" - Búsqueda de dato muy específico con ID conocido
   Ejemplos:
   - "presupuesto del aviso 668461-2025"
   - "deadline de la licitación 12345-2025"
   - Consultas que mencionan un ID específico

3. "general" - Conversación general, saludos, o preguntas que NO requieren documentos
   Ejemplos:
   - "hola", "buenos días", "gracias"
   - "qué es una licitación pública", "cómo funciona el CPV"
   - "explícame qué significa adjudicación"
   - "cómo puedo participar en licitaciones"
   - "qué información tienes", "cómo funciona esto"
   - Preguntas conceptuales o de proceso general

**IMPORTANTE:**
- Si la pregunta es sobre DOCUMENTOS ESPECÍFICOS → "vectorstore"
- Si la pregunta es CONCEPTUAL o GENERAL → "general"
- Si es un saludo o conversación casual → "general"

Responde SOLO con la categoría (vectorstore/specific_lookup/general)."""


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
