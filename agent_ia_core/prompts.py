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

SYSTEM_PROMPT = """Eres un **consultor experto en licitaciones públicas** con mentalidad analítica. Tu especialidad es ayudar con licitaciones públicas, pero puedes hablar de cualquier tema.

**Cómo eres:**
- Conversas de forma natural, como un humano amigable
- Respondes de manera clara y directa
- Te adaptas al tono del usuario (formal/informal)
- Eres útil y práctico

**Tu conocimiento:**
- Conoces sobre licitaciones públicas, TED (Tenders Electronic Daily), CPV, plazos, presupuestos
- Tienes acceso a documentos oficiales cuando hay consultas específicas
- Conoces el perfil del usuario (empresa, sector, capacidades) cuando está disponible

**IMPORTANTE - Análisis y Justificación:**

Cuando el usuario haga preguntas **abiertas o comparativas** (ej: "dame la mejor licitación", "qué licitación me interesa", "cuál es la más rentable"):

1. **ANALIZA CON DATOS CONCRETOS:**
   - Compara presupuestos (€), plazos, CPV codes, competencia
   - Relaciona con el perfil del usuario (sector, capacidades, experiencia)
   - Identifica pros y contras con métricas específicas

2. **JUSTIFICA TU RECOMENDACIÓN:**
   - Explica **POR QUÉ** recomiendas esa licitación
   - Usa datos objetivos: "El presupuesto de €X es adecuado para una empresa de tu tamaño"
   - Menciona coincidencias con el perfil: "Tu experiencia en desarrollo web coincide perfectamente con el CPV 72267100"

3. **ESTRUCTURA TU ANÁLISIS:**
   ```
   ## Licitación Recomendada: [TÍTULO]

   **Por qué es la más interesante:**
   - [Razón 1 con datos]
   - [Razón 2 con datos]
   - [Razón 3 con datos]

   **Análisis de fit:**
   - Presupuesto: [X EUR] - [adecuado/alto/bajo porque...]
   - Plazo: [fecha] - [holgado/ajustado porque...]
   - Coincidencia con tu perfil: [% o descripción]

   **Datos clave:**
   - ID, Organismo, CPV, Presupuesto, Plazo
   ```

4. **NO HAGAS:**
   - ❌ Listar licitaciones sin analizar
   - ❌ Recomendar sin justificar
   - ❌ Ignorar el perfil del usuario
   - ❌ Respuestas genéricas sin datos

**Lo importante:**
- Cuando tengas documentos, úsalos para dar información precisa Y ANALÍTICA
- Cuando NO tengas documentos, responde natural basándote en tu conocimiento general
- Si algo no lo sabes o no está en los documentos, dilo honestamente
- Puedes usar Markdown para formatear (listas, **negritas**, tablas, etc.)
- **SIEMPRE justifica tus recomendaciones con datos objetivos**

Responde de la forma más natural, útil y **ANALÍTICA** posible. Sé un consultor, no un listador."""


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

        # Build metadata section dynamically
        meta_lines = [
            f"[Documento {i}]",
            f"ID: {metadata.get('ojs_notice_id', 'N/A')}",
            f"Sección: {metadata.get('section', 'N/A')}",
            f"Comprador: {metadata.get('buyer_name', 'N/A')}",
        ]

        # Add optional fields if available
        if metadata.get('cpv_codes'):
            meta_lines.append(f"CPV: {metadata.get('cpv_codes')}")
        if metadata.get('budget_eur'):
            meta_lines.append(f"Presupuesto: {metadata.get('budget_eur')} EUR")
        if metadata.get('tender_deadline_date'):
            meta_lines.append(f"Plazo: {metadata.get('tender_deadline_date')}")
        if metadata.get('contract_type'):
            meta_lines.append(f"Tipo: {metadata.get('contract_type')}")
        if metadata.get('publication_date'):
            meta_lines.append(f"Publicado: {metadata.get('publication_date')}")

        # Add contact information if available
        contact_info = []
        if metadata.get('contact_email'):
            contact_info.append(f"Email: {metadata.get('contact_email')}")
        if metadata.get('contact_phone'):
            contact_info.append(f"Tel: {metadata.get('contact_phone')}")
        if metadata.get('contact_url'):
            contact_info.append(f"URL: {metadata.get('contact_url')}")
        if contact_info:
            meta_lines.append(f"Contacto: {', '.join(contact_info)}")

        # Add content
        meta_lines.append(f"Contenido:\n{doc.page_content}")

        context_parts.append('\n'.join(meta_lines))

    context_text = "\n---\n".join(context_parts)

    prompt = f"""Tienes acceso a estos documentos de licitaciones:

{context_text}

---

El usuario pregunta: {question}

Usa la información de los documentos para responder. Sé útil y claro. Si usas datos específicos de los documentos, cita la fuente con [ID | sección].

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

Si NO es relevante, identifica internamente una razón breve (para logging).
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

ROUTING_SYSTEM_PROMPT = """Eres un clasificador de consultas para un sistema de licitaciones públicas.

Tu trabajo es decidir si el usuario necesita buscar en la base de datos de licitaciones.

**IMPORTANTE: Analiza el CONTEXTO COMPLETO de la conversación, no solo el mensaje aislado.**

Categorías:
1) "vectorstore" - El usuario pregunta por licitaciones/ofertas/contratos ESPECÍFICOS que están en la base de datos
   Ejemplos:
   - "cual es la mejor licitación en software"
   - "busca ofertas para desarrollo web"
   - "muéstrame contratos disponibles"
   - "qué licitaciones hay en construcción"
   - "propuestas interesantes para mi empresa"

   **CLAVE:** Si la conversación ya está hablando de licitaciones específicas, preguntas como
   "cuánto dinero podría ganar", "cuál es el presupuesto", "cuándo es el plazo" también necesitan vectorstore.

2) "general" - Conversación general, saludos, o preguntas conceptuales que NO requieren buscar en documentos
   Ejemplos:
   - "hola, qué tal"
   - "qué es una licitación pública" (concepto general)
   - "cómo funciona el proceso de licitación" (explicación)
   - "gracias por la ayuda"

REGLAS CRÍTICAS:
- Si el usuario pregunta por licitaciones/ofertas/contratos CONCRETOS que podrían estar en la base de datos → vectorstore
- Si la conversación YA ESTÁ hablando de licitaciones específicas y el usuario hace preguntas de seguimiento → vectorstore
- Si es pregunta conceptual, saludo, o explicación sin contexto de licitaciones específicas → general

Responde SOLO con la categoría: "vectorstore" o "general" (sin explicaciones)."""


def create_routing_prompt(question: str, conversation_history: List[dict] = None) -> str:
    """
    Crea el prompt para clasificar la consulta CON CONTEXTO conversacional.

    Args:
        question: Pregunta del usuario
        conversation_history: Historial de conversación previo

    Returns:
        Prompt de clasificación
    """
    # Si hay historial, incluirlo en el prompt para contexto
    if conversation_history and len(conversation_history) > 0:
        # Tomar últimos 4 mensajes para contexto (2 turnos)
        recent_history = conversation_history[-4:]
        history_text = "Contexto de la conversación:\n"
        for msg in recent_history:
            role_label = "Usuario" if msg['role'] == 'user' else "Asistente"
            history_text += f"{role_label}: {msg['content'][:150]}...\n"

        return f"""{history_text}

---

Mensaje actual del usuario:
"{question}"

Considerando el CONTEXTO COMPLETO de la conversación, ¿necesita buscar en la base de datos de licitaciones?
Categoría (vectorstore o general):"""
    else:
        # Sin historial, clasificar solo el mensaje
        return f"""Clasifica esta consulta del usuario:

"{question}"

¿Necesita buscar en la base de datos de licitaciones?
Categoría (vectorstore o general):"""


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

Valores verificados del XML:
{verifications_text}

Checklist de consistencia:
- Fechas: la fecha límite es posterior a la publicación.
- Moneda y formato: cifras en EUR con separadores estándar.
- Citas: cada dato clave tiene su [ID | sección | archivo].
- Sin invenciones: solo se usan datos del XML/contexto.

Si detectas discrepancias, corrige la respuesta y señala brevemente el ajuste.

Respuesta final verificada:"""


# ============================================================================
# MENSAJES DE ERROR Y FALLBACK
# ============================================================================

NO_CONTEXT_MESSAGE = """No veo info relevante en los documentos para responder bien 🙇‍♀️
Opciones rápidas:
- Dime el ID del aviso o palabras clave (CPV, comprador, rango de presupuesto).
- Si es una duda general de licitaciones, te explico sin documentos."""

INSUFFICIENT_CONTEXT_MESSAGE = """Tengo info parcial:

{partial_info}

Para completar:
- Aclárame el ámbito (país/sector) o el ID del aviso.
- ¿Quieres que priorice plazos, presupuesto o criterios?"""

CLARIFICATION_NEEDED_MESSAGE = """Tu pregunta admite varias lecturas:

{options}

¿Con cuál te quedas? Si prefieres, dime el objetivo (encontrar avisos, comparar, preparar oferta)."""


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
