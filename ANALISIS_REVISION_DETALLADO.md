# Análisis Detallado del Sistema de Revisión - TenderAI Platform

## 📋 Índice
1. [Flujo Completo de Ejecución](#flujo-completo-de-ejecución)
2. [Qué se le Pasa al Revisor (Detalles Técnicos)](#qué-se-le-pasa-al-revisor-detalles-técnicos)
3. [Prompt Completo del Revisor](#prompt-completo-del-revisor)
4. [Prompt de Mejora del Agente](#prompt-de-mejora-del-agente)
5. [Verificación del Sistema de Logging](#verificación-del-sistema-de-logging)
6. [Ejemplo de Ejecución Completa](#ejemplo-de-ejecución-completa)

---

## 1. Flujo Completo de Ejecución

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. Usuario envía pregunta                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│         2. Agente Principal ejecuta query inicial               │
│         - Busca documentos en vectorstore                       │
│         - Llama tools necesarias                                │
│         - Genera respuesta inicial                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              LOOP 1: REVISIÓN OBLIGATORIA                       │
│                                                                  │
│  3. Revisor LLM recibe:                                         │
│     • user_question: "¿licitaciones de software IA?"            │
│     • conversation_history: [últimos 5 mensajes]                │
│     • initial_response: "## Licitación 001234..."              │
│     • metadata: {                                               │
│         documents_used: [doc1, doc2, doc3],                     │
│         tools_used: ["find_top_tenders"],                       │
│         route: "agent"                                          │
│       }                                                          │
│                                                                  │
│  4. Revisor LLM analiza y devuelve:                             │
│     {                                                            │
│       "status": "NEEDS_IMPROVEMENT",                            │
│       "score": 72,                                              │
│       "issues": [                                               │
│         "Falta presupuesto en licitación 001234"                │
│       ],                                                         │
│       "suggestions": [                                           │
│         "Añadir información de plazos"                          │
│       ],                                                         │
│       "tool_suggestions": [                                      │
│         {                                                        │
│           "tool": "get_tender_details",                         │
│           "params": {"tender_id": "001234"},                    │
│           "reason": "Obtener presupuesto detallado"             │
│         }                                                        │
│       ],                                                         │
│       "param_validation": [                                      │
│         {                                                        │
│           "tool": "find_top_tenders",                           │
│           "param": "limit",                                     │
│           "issue": "Límite de 10 puede ser excesivo",          │
│           "suggested": "5"                                      │
│         }                                                        │
│       ],                                                         │
│       "feedback": "Falta incluir presupuestos y plazos..."     │
│     }                                                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              5. Agente Principal - Query de Mejora              │
│                                                                  │
│  Se le pasa un prompt de mejora con:                            │
│  • Tu respuesta actual: [respuesta completa]                    │
│  • Problemas detectados: [lista de issues]                      │
│  • Sugerencias: [lista de suggestions]                          │
│  • Herramientas recomendadas:                                   │
│    - get_tender_details: Obtener presupuesto detallado          │
│      Parámetros sugeridos: {"tender_id": "001234"}              │
│  • Validación de parámetros:                                    │
│    - find_top_tenders - parámetro 'limit': Excesivo            │
│      Valor sugerido: 5                                          │
│  • Feedback: [texto explicativo del revisor]                    │
│                                                                  │
│  Historial incluye:                                             │
│  - Conversación anterior completa                               │
│  - Pregunta original del usuario                                │
│  - Respuesta actual (como assistant message)                    │
│                                                                  │
│  6. Agente ejecuta:                                             │
│     - Llama get_tender_details("001234")                        │
│     - Obtiene presupuesto: €500,000                             │
│     - Genera respuesta mejorada con todos los datos             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LOOP 2: REVISIÓN OPCIONAL                      │
│                  (solo si score < 95 y loops < max)             │
│                                                                  │
│  7. Se repite el proceso con la respuesta mejorada              │
│                                                                  │
│  Si score >= 95: ✓ APROBADO, se termina                        │
│  Si loops >= max_review_loops: ✓ Se termina                    │
│  Si no: Se ejecuta otro loop de mejora                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 8. Respuesta Final al Usuario                   │
│                                                                  │
│  Se retorna:                                                     │
│  - Respuesta mejorada final                                     │
│  - Metadata completo:                                            │
│    • documents: todos los documentos usados                     │
│    • tools_used: todas las tools llamadas                       │
│    • iterations: número total de iteraciones                    │
│    • review_tracking: {                                         │
│        review_performed: true,                                  │
│        max_loops: 3,                                            │
│        loops_executed: 2,                                       │
│        improvement_applied: true,                               │
│        all_scores: [72, 89],                                    │
│        final_score: 89,                                         │
│        review_history: [{loop 1}, {loop 2}]                     │
│      }                                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Qué se le Pasa al Revisor (Detalles Técnicos)

### 📍 Ubicación en el código: `apps/chat/services.py:465-470`

```python
review_result = reviewer.review_response(
    user_question=message,              # ← STRING
    conversation_history=formatted_history,  # ← LIST[DICT]
    initial_response=response_content,  # ← STRING
    metadata=review_metadata_input      # ← DICT
)
```

### 🔍 Desglose Detallado de Cada Parámetro

#### **1. user_question** (STRING)
**Qué es:** La pregunta ORIGINAL que hizo el usuario al agente.

**Ejemplo:**
```
"Busca licitaciones de desarrollo de software con inteligencia artificial"
```

**Por qué es importante:** El revisor necesita saber qué preguntó realmente el usuario para verificar si la respuesta del agente está alineada.

---

#### **2. conversation_history** (LIST[DICT])
**Qué es:** Los últimos 5 mensajes de la conversación (limitado para no saturar).

**Formato:**
```python
[
    {
        'role': 'user',
        'content': 'Hola, necesito licitaciones de IA'
    },
    {
        'role': 'assistant',
        'content': 'Claro, buscando licitaciones...'
    },
    {
        'role': 'user',
        'content': 'Busca licitaciones de desarrollo de software con inteligencia artificial'
    }
]
```

**Construcción:** En `apps/chat/services.py:388-403`:
```python
formatted_history = []
for msg in recent_messages:
    formatted_history.append({
        'role': msg.role,
        'content': msg.content
    })
```

**Por qué es importante:** El revisor necesita contexto de la conversación para entender si la respuesta es coherente con el hilo de la discusión.

---

#### **3. initial_response** (STRING)
**Qué es:** El texto completo de la respuesta generada por el agente principal.

**Ejemplo:**
```markdown
## Licitación 001234-2025 - Desarrollo de Software IA

**Organismo:** Ministerio de Economía
**Presupuesto:** No especificado
**Plazo de presentación:** 15/03/2025

Esta licitación busca el desarrollo de un sistema de inteligencia artificial...
```

**Por qué es importante:** Es LO QUE VA A REVISAR. El revisor analiza este texto para detectar problemas de formato, contenido faltante, errores, etc.

---

#### **4. metadata** (DICT)
**Qué es:** Metadatos sobre los recursos usados por el agente.

**Construcción:** En `apps/chat/services.py:458-462`:
```python
review_metadata_input = {
    'documents_used': result.get('documents', []),
    'tools_used': result.get('tools_used', []),
    'route': result.get('route', 'unknown')
}
```

**Contenido detallado:**

```python
{
    'documents_used': [
        {
            'id': '001234-2025',
            'ojs_notice_id': '001234-2025-ES',
            'title': 'Desarrollo de Software IA',
            'section': 'Descripción General',
            'content': 'El Ministerio busca un sistema de IA...',
            'similarity_score': 0.89,
            'budget_amount': 500000.0,
            'submission_deadline': '2025-03-15',
            'created_at': '2025-01-10T10:30:00'
        },
        {
            'id': '002345-2025',
            'ojs_notice_id': '002345-2025-ES',
            'title': 'Consultoría IA Educativa',
            'section': 'Requisitos Técnicos',
            'content': 'Se requiere desarrollo de modelos ML...',
            'similarity_score': 0.85,
            'budget_amount': 300000.0,
            'submission_deadline': '2025-03-20',
            'created_at': '2025-01-12T14:20:00'
        }
    ],
    'tools_used': [
        'find_top_tenders',
        'get_tender_details'
    ],
    'route': 'agent'
}
```

**Por qué es importante:** El revisor puede ver:
- Cuántos documentos consultó el agente (¿fueron suficientes?)
- Qué herramientas usó (¿usó las correctas?)
- Qué información está disponible en los documentos (¿el agente mencionó todo lo importante?)

---

## 3. Prompt Completo del Revisor

### 📍 Ubicación: `apps/chat/response_reviewer.py:121-212`

El revisor recibe un prompt estructurado que se construye así:

```python
def _build_review_prompt(self, user_question, conversation_history, initial_response, metadata):
    # Formatear historial (últimos 5 mensajes)
    history_text = self._format_conversation_history(conversation_history)

    # Información de documentos
    docs_info = f"\n\n**Documentos consultados:** {len(metadata['documents_used'])} documentos"
    docs_ids = [doc.get('id', 'unknown') for doc in metadata['documents_used'][:5]]
    docs_info += f"\nIDs: {', '.join(docs_ids)}"

    # Información de tools
    tools_info = f"\n\n**Herramientas usadas:** {', '.join(metadata['tools_used'])}"
```

### 📄 Prompt Completo Enviado al LLM Revisor:

```
Eres un **revisor experto de respuestas de chatbot sobre licitaciones públicas**.

Tu tarea es revisar la respuesta generada por el agente principal y determinar si está bien o necesita mejoras.

**CONTEXTO DE LA CONVERSACIÓN:**

Historial:
Usuario: Hola, necesito licitaciones de IA
Asistente: Claro, buscando licitaciones...
Usuario: Busca licitaciones de desarrollo de software con inteligencia artificial

Pregunta actual del usuario:
"Busca licitaciones de desarrollo de software con inteligencia artificial"

**Documentos consultados:** 3 documentos
IDs: 001234-2025, 002345-2025, 003456-2025

**Herramientas usadas:** find_top_tenders, get_tender_details

---

**RESPUESTA GENERADA POR EL AGENTE:**

## Licitación 001234-2025 - Desarrollo de Software IA

**Organismo:** Ministerio de Economía
**Presupuesto:** No especificado
**Plazo de presentación:** 15/03/2025

Esta licitación busca el desarrollo de un sistema de inteligencia artificial...

---

**TU TAREA:**

Analiza la respuesta y evalúa:

1. **FORMATO (30 puntos):**
   - ¿Usa Markdown correctamente?
   - Si hay múltiples licitaciones, ¿usa ## para cada una? (NO listas numeradas 1. 2. 3.)
   - ¿Está bien estructurado y es legible?

2. **CONTENIDO (40 puntos):**
   - ¿Responde completamente a la pregunta del usuario?
   - ¿Incluye todos los datos relevantes (IDs, presupuestos, plazos)?
   - ¿Falta información importante que debería estar?

3. **ANÁLISIS (30 puntos):**
   - Si el usuario pidió recomendaciones, ¿justifica con datos?
   - ¿Usa los documentos consultados correctamente?
   - ¿Es útil y profesional?

**INSTRUCCIONES DE RESPUESTA:**

Responde EXACTAMENTE en este formato:

```
STATUS: [APPROVED o NEEDS_IMPROVEMENT]
SCORE: [0-100]

ISSUES:
- [Problema 1 si existe]
- [Problema 2 si existe]
(Si no hay problemas, escribe: Ninguno)

SUGGESTIONS:
- [Sugerencia 1 si existe]
- [Sugerencia 2 si existe]
(Si no hay sugerencias, escribe: Ninguna)

TOOL_SUGGESTIONS:
- tool: [nombre_tool], params: {parametros}, reason: [razón por la que debe llamarla]
- tool: [nombre_tool], params: {parametros}, reason: [razón]
(Si no necesita llamar tools adicionales, escribe: Ninguna)

PARAM_VALIDATION:
- tool: [nombre_tool_ya_ejecutada], param: [nombre_parametro], issue: [problema con el parámetro], suggested: [valor sugerido]
(Si los parámetros de las tools ejecutadas están bien, escribe: Ninguna)

FEEDBACK:
[Si STATUS = NEEDS_IMPROVEMENT, explica QUÉ debe mejorar el agente principal.
Si STATUS = APPROVED, deja esta sección vacía o escribe "Respuesta correcta"]
```

**IMPORTANTE:**
- Si score >= 75 → STATUS debe ser APPROVED
- Si score < 75 → STATUS debe ser NEEDS_IMPROVEMENT
- En FEEDBACK, sé específico: "Falta incluir el presupuesto de la licitación 00123456"
- En TOOL_SUGGESTIONS, recomienda tools específicas que ayudarían a mejorar la respuesta
- En PARAM_VALIDATION, verifica si los parámetros de las tools ya ejecutadas fueron óptimos
- NO reescribas la respuesta, solo da feedback al agente para que él la mejore

**HERRAMIENTAS DISPONIBLES:**
- find_best_tender(query): Encuentra LA mejor licitación (singular)
- find_top_tenders(query, limit): Encuentra X mejores licitaciones (plural)
- get_tender_details(tender_id): Obtiene información detallada de una licitación específica
- find_by_budget(min_budget, max_budget): Busca por rango de presupuesto
- find_by_deadline(days_ahead): Busca por fecha límite
- get_company_info(): Obtiene información de la empresa del usuario
- compare_tenders(tender_ids): Compara múltiples licitaciones

**NOTA:** El agente ejecutará al menos UNA iteración de mejora.
Proporciona sugerencias constructivas y específicas sobre qué tools llamar o qué mejorar.
```

### 🔄 Respuesta Esperada del Revisor:

```
STATUS: NEEDS_IMPROVEMENT
SCORE: 72

ISSUES:
- Falta incluir el presupuesto de la licitación 001234-2025
- No se menciona ningún requisito técnico específico

SUGGESTIONS:
- Incluir presupuestos para todas las licitaciones mencionadas
- Añadir sección de requisitos técnicos de cada licitación

TOOL_SUGGESTIONS:
- tool: get_tender_details, params: {"tender_id": "001234-2025"}, reason: Obtener presupuesto y requisitos completos
- tool: get_tender_details, params: {"tender_id": "002345-2025"}, reason: Obtener detalles completos de la segunda licitación

PARAM_VALIDATION:
- tool: find_top_tenders, param: limit, issue: Límite de 10 puede ser excesivo para la pregunta del usuario, suggested: 5

FEEDBACK:
La respuesta está bien estructurada pero falta información crítica. El usuario preguntó por licitaciones de IA y se encontraron 3 documentos relevantes, pero en la respuesta solo aparece el presupuesto de una de ellas, y dice "No especificado". Sin embargo, en los metadatos puedo ver que el documento 001234-2025 SÍ tiene budget_amount: 500000.0. Debes llamar a get_tender_details para obtener esta información completa y mostrarla al usuario. También sería útil incluir requisitos técnicos que están disponibles en el documento 002345-2025 sección "Requisitos Técnicos".
```

---

## 4. Prompt de Mejora del Agente

### 📍 Ubicación: `apps/chat/services.py:530-557`

Una vez que el revisor devuelve sus sugerencias, el **Agente Principal** recibe un prompt de mejora:

```python
improvement_prompt = f"""Tu respuesta anterior fue revisada (Loop {current_loop}/{max_review_loops}). Vamos a mejorarla.

**Tu respuesta actual:**
{response_content}

**Problemas detectados:**
{issues_list if issues_list else '- Ningún problema grave detectado'}

**Sugerencias:**
{suggestions_list if suggestions_list else '- Mantener el buen formato actual'}
{tool_suggestions_section}{param_validation_section}
{feedback_section}

**Tu tarea:**
Genera una respuesta MEJORADA que sea aún más completa y útil.

**IMPORTANTE:**
- Usa herramientas (tools) si necesitas buscar más información
- El revisor ha sugerido herramientas específicas arriba - ÚSALAS si son relevantes
- Si faltan datos específicos (presupuestos, plazos, etc.), búscalos con las tools apropiadas
- Si el formato es incorrecto, corrígelo (usa ## para licitaciones múltiples, NO listas numeradas)
- Si falta análisis, justifica tus recomendaciones con datos concretos
- Si ya está bien, puedes añadir más detalles útiles o mejorar la presentación

**Pregunta original del usuario:**
{message}

Genera tu respuesta mejorada:"""
```

### 📄 Ejemplo de Prompt Completo Enviado al Agente:

```
Tu respuesta anterior fue revisada (Loop 1/3). Vamos a mejorarla.

**Tu respuesta actual:**
## Licitación 001234-2025 - Desarrollo de Software IA

**Organismo:** Ministerio de Economía
**Presupuesto:** No especificado
**Plazo de presentación:** 15/03/2025

Esta licitación busca el desarrollo de un sistema de inteligencia artificial...

**Problemas detectados:**
- Falta incluir el presupuesto de la licitación 001234-2025
- No se menciona ningún requisito técnico específico

**Sugerencias:**
- Incluir presupuestos para todas las licitaciones mencionadas
- Añadir sección de requisitos técnicos de cada licitación

**Herramientas recomendadas por el revisor:**
- get_tender_details: Obtener presupuesto y requisitos completos
  Parámetros sugeridos: {"tender_id": "001234-2025"}
- get_tender_details: Obtener detalles completos de la segunda licitación
  Parámetros sugeridos: {"tender_id": "002345-2025"}

**Validación de parámetros de tools ya ejecutadas:**
- find_top_tenders - parámetro 'limit': Límite de 10 puede ser excesivo para la pregunta del usuario
  Valor sugerido: 5

**Feedback del revisor:**
La respuesta está bien estructurada pero falta información crítica. El usuario preguntó por licitaciones de IA y se encontraron 3 documentos relevantes, pero en la respuesta solo aparece el presupuesto de una de ellas, y dice "No especificado". Sin embargo, en los metadatos puedo ver que el documento 001234-2025 SÍ tiene budget_amount: 500000.0. Debes llamar a get_tender_details para obtener esta información completa y mostrarla al usuario. También sería útil incluir requisitos técnicos que están disponibles en el documento 002345-2025 sección "Requisitos Técnicos".

**Tu tarea:**
Genera una respuesta MEJORADA que sea aún más completa y útil.

**IMPORTANTE:**
- Usa herramientas (tools) si necesitas buscar más información
- El revisor ha sugerido herramientas específicas arriba - ÚSALAS si son relevantes
- Si faltan datos específicos (presupuestos, plazos, etc.), búscalos con las tools apropiadas
- Si el formato es incorrecto, corrígelo (usa ## para licitaciones múltiples, NO listas numeradas)
- Si falta análisis, justifica tus recomendaciones con datos concretos
- Si ya está bien, puedes añadir más detalles útiles o mejorar la presentación

**Pregunta original del usuario:**
Busca licitaciones de desarrollo de software con inteligencia artificial

Genera tu respuesta mejorada:
```

### 🔄 Historial Completo Enviado al Agente:

En `apps/chat/services.py:561-564`:
```python
improvement_history = formatted_history + [
    {'role': 'user', 'content': message},
    {'role': 'assistant', 'content': response_content}
]
```

**Contenido del historial:**
```python
[
    {'role': 'user', 'content': 'Hola, necesito licitaciones de IA'},
    {'role': 'assistant', 'content': 'Claro, buscando licitaciones...'},
    {'role': 'user', 'content': 'Busca licitaciones de desarrollo de software con inteligencia artificial'},
    {'role': 'assistant', 'content': '## Licitación 001234-2025 - Desarrollo de Software IA\n\n**Organismo:** Ministerio...'}
]
```

**Esto permite que el agente:**
1. Recuerde toda la conversación anterior
2. Vea su respuesta anterior completa
3. Entienda el contexto completo antes de mejorar

---

## 5. Verificación del Sistema de Logging

### ✅ Sistema de Logging Actual: `apps/core/logging_config.py`

El `ChatLogger` está diseñado para capturar **TODO** lo que se envía y recibe de los LLMs.

### 📊 Métodos de Logging Disponibles:

#### 1. **log_llm_request()** (líneas 68-92)
**Qué registra:**
- Proveedor y modelo del LLM (ej: "ollama/qwen2.5:72b")
- **TODOS los mensajes enviados al LLM** (role + content)
- **TODAS las herramientas disponibles** (name + description)

**Formato en el log:**
```
================================================================================
LLM REQUEST → ollama/qwen2.5:72b
================================================================================
MESSAGES:
  [0] Role: system
      Eres un asistente experto en licitaciones públicas...
  [1] Role: user
      Busca licitaciones de desarrollo de software con inteligencia artificial
  [2] Role: assistant
      ## Licitación 001234-2025 - Desarrollo de Software IA...
  [3] Role: user
      Tu respuesta anterior fue revisada (Loop 1/3). Vamos a mejorarla...

TOOLS AVAILABLE:
  [0] find_top_tenders
      Description: Busca las X mejores licitaciones que coincidan con la consulta
  [1] get_tender_details
      Description: Obtiene información completa de una licitación específica
  ...
```

#### 2. **log_llm_response()** (líneas 93-118)
**Qué registra:**
- **Respuesta COMPLETA del LLM** (serializada en JSON)
- Incluyendo tool_calls, content, finish_reason, tokens, etc.

**Formato en el log:**
```
================================================================================
LLM RESPONSE ←
================================================================================
{
  "content": "## Licitación 001234-2025 - Desarrollo de Software IA\n\n**Organismo:** Ministerio de Economía\n**Presupuesto:** €500,000\n...",
  "additional_kwargs": {
    "tool_calls": [
      {
        "id": "call_abc123",
        "function": {
          "name": "get_tender_details",
          "arguments": "{\"tender_id\": \"001234-2025\"}"
        }
      }
    ]
  },
  "response_metadata": {
    "model": "qwen2.5:72b",
    "finish_reason": "tool_calls",
    "total_tokens": 1234,
    "input_tokens": 890,
    "output_tokens": 344
  }
}
```

#### 3. **log_tool_execution_summary()** (líneas 165-236)
**Qué registra:**
- Resumen completo de TODAS las tools ejecutadas
- Parámetros de entrada de cada tool
- Resultados de cada tool
- Estado de éxito/fallo
- Reintentos si los hubo

**Formato en el log:**
```
================================================================================
TOOL EXECUTION SUMMARY
================================================================================
Total tools executed: 4

Tool usage breakdown:
  - find_top_tenders: 1x
  - get_tender_details: 3x

Detailed execution sequence:

  1. ✓ find_top_tenders
     Parameters:
       {
         "query": "desarrollo software inteligencia artificial",
         "limit": 5
       }
     Result:
       - success: True
       - count: 3
       - document_ids: ['001234-2025', '002345-2025', '003456-2025']

  2. ✓ get_tender_details
     Parameters:
       {
         "tender_id": "001234-2025"
       }
     Result:
       - success: True
       - document_id: 001234-2025

  3. ✓ get_tender_details (Iteration 2)
     Parameters:
       {
         "tender_id": "002345-2025"
       }
     Result:
       - success: True
       - document_id: 002345-2025

  4. ✗ get_tender_details (Iteration 3)
     Parameters:
       {
         "tender_id": "999999-2025"
       }
     Result:
       - success: False
       - total_attempts: 3 (reintentos: 2)
       - retries_exhausted: True ⚠️
       - error: No se encontró la licitación con ID 999999-2025

================================================================================
```

#### 4. **log_assistant_message()** (líneas 238-249)
**Qué registra:**
- Mensaje final del asistente
- **Metadatos completos** (documents, tools_used, review_tracking, etc.)

**Formato en el log:**
```
================================================================================
ASSISTANT MESSAGE
================================================================================
## Licitación 001234-2025 - Desarrollo de Software IA

**Organismo:** Ministerio de Economía
**Presupuesto:** €500,000
**Plazo de presentación:** 15/03/2025

...

METADATA:
{
  "documents": [
    {
      "id": "001234-2025",
      "title": "Desarrollo de Software IA",
      "budget_amount": 500000.0,
      "similarity_score": 0.89
    }
  ],
  "tools_used": [
    "find_top_tenders",
    "get_tender_details"
  ],
  "iterations": 8,
  "review_tracking": {
    "review_performed": true,
    "max_loops": 3,
    "loops_executed": 2,
    "improvement_applied": true,
    "all_scores": [72, 89],
    "final_score": 89,
    "review_history": [
      {
        "loop": 1,
        "status": "NEEDS_IMPROVEMENT",
        "score": 72,
        "issues": ["Falta presupuesto..."],
        "suggestions": ["Añadir presupuestos..."]
      },
      {
        "loop": 2,
        "status": "APPROVED",
        "score": 89,
        "issues": [],
        "suggestions": []
      }
    ]
  }
}
```

### ⚠️ **PROBLEMA DETECTADO: Falta logging del Revisor LLM**

Actualmente, el código NO está logueando las llamadas al LLM Revisor. Aquí está la ubicación del problema:

**`apps/chat/response_reviewer.py:71-73`:**
```python
# Llamar al LLM revisor
logger.info("[REVIEWER] Llamando al LLM revisor...")
review_result = self.llm.invoke(review_prompt)  # ← NO SE LOGUEA
```

**Esto significa que NO se está registrando:**
- El prompt completo enviado al revisor
- La respuesta completa del revisor (antes de parsearla)

### ✅ **SOLUCIÓN NECESARIA:**

Necesitamos añadir logging en el ResponseReviewer para capturar:
1. El prompt completo que se envía al revisor
2. La respuesta raw del revisor antes de parsearla

---

## 6. Ejemplo de Ejecución Completa

### Escenario: Usuario pregunta "Busca licitaciones de software IA"

#### **Paso 1: Usuario envía mensaje**
```
2025-01-28 10:30:15 | INFO | ================================================================================
2025-01-28 10:30:15 | INFO | USER MESSAGE (session 42)
2025-01-28 10:30:15 | INFO | ================================================================================
2025-01-28 10:30:15 | INFO | Busca licitaciones de desarrollo de software con inteligencia artificial
```

#### **Paso 2: Agente ejecuta query inicial**
```
2025-01-28 10:30:16 | INFO | ================================================================================
2025-01-28 10:30:16 | INFO | LLM REQUEST → ollama/qwen2.5:72b
2025-01-28 10:30:16 | INFO | ================================================================================
2025-01-28 10:30:16 | INFO | MESSAGES:
2025-01-28 10:30:16 | INFO |   [0] Role: system
2025-01-28 10:30:16 | INFO |       Eres un asistente experto en licitaciones públicas...
2025-01-28 10:30:16 | INFO |   [1] Role: user
2025-01-28 10:30:16 | INFO |       Busca licitaciones de desarrollo de software con inteligencia artificial
2025-01-28 10:30:16 | INFO |
2025-01-28 10:30:16 | INFO | TOOLS AVAILABLE:
2025-01-28 10:30:16 | INFO |   [0] find_top_tenders
2025-01-28 10:30:16 | INFO |   [1] get_tender_details
2025-01-28 10:30:16 | INFO |   [2] find_by_budget
...
```

```
2025-01-28 10:30:18 | INFO | ================================================================================
2025-01-28 10:30:18 | INFO | LLM RESPONSE ←
2025-01-28 10:30:18 | INFO | ================================================================================
2025-01-28 10:30:18 | INFO | {
2025-01-28 10:30:18 | INFO |   "content": "",
2025-01-28 10:30:18 | INFO |   "additional_kwargs": {
2025-01-28 10:30:18 | INFO |     "tool_calls": [
2025-01-28 10:30:18 | INFO |       {
2025-01-28 10:30:18 | INFO |         "function": {
2025-01-28 10:30:18 | INFO |           "name": "find_top_tenders",
2025-01-28 10:30:18 | INFO |           "arguments": "{\"query\": \"desarrollo software inteligencia artificial\", \"limit\": 10}"
2025-01-28 10:30:18 | INFO |         }
2025-01-28 10:30:18 | INFO |       }
2025-01-28 10:30:18 | INFO |     ]
2025-01-28 10:30:18 | INFO |   }
2025-01-28 10:30:18 | INFO | }
```

```
2025-01-28 10:30:19 | INFO | --------------------------------------------------------------------------------
2025-01-28 10:30:19 | INFO | TOOL CALL: find_top_tenders (Iteration 1)
2025-01-28 10:30:19 | INFO | --------------------------------------------------------------------------------
2025-01-28 10:30:19 | INFO | INPUT PARAMETERS:
2025-01-28 10:30:19 | INFO |   {
2025-01-28 10:30:19 | INFO |     "query": "desarrollo software inteligencia artificial",
2025-01-28 10:30:19 | INFO |     "limit": 10
2025-01-28 10:30:19 | INFO |   }
```

```
2025-01-28 10:30:22 | INFO | --------------------------------------------------------------------------------
2025-01-28 10:30:22 | INFO | TOOL RESULT: find_top_tenders [✓ SUCCESS] (Iteration 1)
2025-01-28 10:30:22 | INFO | --------------------------------------------------------------------------------
2025-01-28 10:30:22 | INFO |   {
2025-01-28 10:30:22 | INFO |     "success": true,
2025-01-28 10:30:22 | INFO |     "count": 3,
2025-01-28 10:30:22 | INFO |     "results": [
2025-01-28 10:30:22 | INFO |       {"id": "001234-2025", "title": "Desarrollo Software IA", "similarity": 0.89},
2025-01-28 10:30:22 | INFO |       {"id": "002345-2025", "title": "Consultoría IA Educativa", "similarity": 0.85},
2025-01-28 10:30:22 | INFO |       {"id": "003456-2025", "title": "Plataforma ML Sanitaria", "similarity": 0.82}
2025-01-28 10:30:22 | INFO |     ]
2025-01-28 10:30:22 | INFO |   }
```

*(El agente genera respuesta final)*

```
2025-01-28 10:30:30 | INFO | ================================================================================
2025-01-28 10:30:30 | INFO | LLM RESPONSE ←
2025-01-28 10:30:30 | INFO | ================================================================================
2025-01-28 10:30:30 | INFO | {
2025-01-28 10:30:30 | INFO |   "content": "## Licitación 001234-2025 - Desarrollo de Software IA\n\n**Organismo:** Ministerio de Economía\n**Presupuesto:** No especificado\n**Plazo:** 15/03/2025\n\n...",
2025-01-28 10:30:30 | INFO |   "additional_kwargs": {},
2025-01-28 10:30:30 | INFO |   "finish_reason": "stop"
2025-01-28 10:30:30 | INFO | }
```

#### **Paso 3: LOOP 1 - Revisión Obligatoria**

**⚠️ ACTUALMENTE NO SE LOGUEA ESTO (necesitamos añadirlo):**
```
2025-01-28 10:30:31 | INFO | ================================================================================
2025-01-28 10:30:31 | INFO | REVIEWER LLM REQUEST → ollama/qwen2.5:72b
2025-01-28 10:30:31 | INFO | ================================================================================
2025-01-28 10:30:31 | INFO | MESSAGES:
2025-01-28 10:30:31 | INFO |   [0] Role: user
2025-01-28 10:30:31 | INFO |       Eres un **revisor experto de respuestas de chatbot sobre licitaciones públicas**...
2025-01-28 10:30:31 | INFO |
2025-01-28 10:30:31 | INFO |       **CONTEXTO DE LA CONVERSACIÓN:**
2025-01-28 10:30:31 | INFO |
2025-01-28 10:30:31 | INFO |       Historial:
2025-01-28 10:30:31 | INFO |       Usuario: Busca licitaciones de desarrollo de software con inteligencia artificial
2025-01-28 10:30:31 | INFO |
2025-01-28 10:30:31 | INFO |       Pregunta actual del usuario:
2025-01-28 10:30:31 | INFO |       "Busca licitaciones de desarrollo de software con inteligencia artificial"
2025-01-28 10:30:31 | INFO |
2025-01-28 10:30:31 | INFO |       **Documentos consultados:** 3 documentos
2025-01-28 10:30:31 | INFO |       IDs: 001234-2025, 002345-2025, 003456-2025
2025-01-28 10:30:31 | INFO |
2025-01-28 10:30:31 | INFO |       **Herramientas usadas:** find_top_tenders
2025-01-28 10:30:31 | INFO |
2025-01-28 10:30:31 | INFO |       ---
2025-01-28 10:30:31 | INFO |
2025-01-28 10:30:31 | INFO |       **RESPUESTA GENERADA POR EL AGENTE:**
2025-01-28 10:30:31 | INFO |
2025-01-28 10:30:31 | INFO |       ## Licitación 001234-2025 - Desarrollo de Software IA
2025-01-28 10:30:31 | INFO |
2025-01-28 10:30:31 | INFO |       **Organismo:** Ministerio de Economía
2025-01-28 10:30:31 | INFO |       **Presupuesto:** No especificado
2025-01-28 10:30:31 | INFO |       ...
```

```
2025-01-28 10:30:35 | INFO | ================================================================================
2025-01-28 10:30:35 | INFO | REVIEWER LLM RESPONSE ←
2025-01-28 10:30:35 | INFO | ================================================================================
2025-01-28 10:30:35 | INFO | STATUS: NEEDS_IMPROVEMENT
2025-01-28 10:30:35 | INFO | SCORE: 72
2025-01-28 10:30:35 | INFO |
2025-01-28 10:30:35 | INFO | ISSUES:
2025-01-28 10:30:35 | INFO | - Falta incluir el presupuesto de la licitación 001234-2025
2025-01-28 10:30:35 | INFO | - No se menciona ningún requisito técnico específico
2025-01-28 10:30:35 | INFO |
2025-01-28 10:30:35 | INFO | SUGGESTIONS:
2025-01-28 10:30:35 | INFO | - Incluir presupuestos para todas las licitaciones mencionadas
2025-01-28 10:30:35 | INFO | - Añadir sección de requisitos técnicos de cada licitación
2025-01-28 10:30:35 | INFO |
2025-01-28 10:30:35 | INFO | TOOL_SUGGESTIONS:
2025-01-28 10:30:35 | INFO | - tool: get_tender_details, params: {"tender_id": "001234-2025"}, reason: Obtener presupuesto y requisitos completos
2025-01-28 10:30:35 | INFO |
2025-01-28 10:30:35 | INFO | PARAM_VALIDATION:
2025-01-28 10:30:35 | INFO | - tool: find_top_tenders, param: limit, issue: Límite de 10 puede ser excesivo, suggested: 5
2025-01-28 10:30:35 | INFO |
2025-01-28 10:30:35 | INFO | FEEDBACK:
2025-01-28 10:30:35 | INFO | La respuesta está bien estructurada pero falta información crítica...
```

#### **Paso 4: Mejora del Agente**

```
2025-01-28 10:30:36 | INFO | ================================================================================
2025-01-28 10:30:36 | INFO | LLM REQUEST → ollama/qwen2.5:72b
2025-01-28 10:30:36 | INFO | ================================================================================
2025-01-28 10:30:36 | INFO | MESSAGES:
2025-01-28 10:30:36 | INFO |   [0] Role: system
2025-01-28 10:30:36 | INFO |       Eres un asistente experto en licitaciones públicas...
2025-01-28 10:30:36 | INFO |   [1] Role: user
2025-01-28 10:30:36 | INFO |       Busca licitaciones de desarrollo de software con inteligencia artificial
2025-01-28 10:30:36 | INFO |   [2] Role: assistant
2025-01-28 10:30:36 | INFO |       ## Licitación 001234-2025 - Desarrollo de Software IA...
2025-01-28 10:30:36 | INFO |   [3] Role: user
2025-01-28 10:30:36 | INFO |       Tu respuesta anterior fue revisada (Loop 1/3). Vamos a mejorarla.
2025-01-28 10:30:36 | INFO |
2025-01-28 10:30:36 | INFO |       **Tu respuesta actual:**
2025-01-28 10:30:36 | INFO |       ## Licitación 001234-2025 - Desarrollo de Software IA...
2025-01-28 10:30:36 | INFO |
2025-01-28 10:30:36 | INFO |       **Problemas detectados:**
2025-01-28 10:30:36 | INFO |       - Falta incluir el presupuesto de la licitación 001234-2025
2025-01-28 10:30:36 | INFO |       - No se menciona ningún requisito técnico específico
2025-01-28 10:30:36 | INFO |
2025-01-28 10:30:36 | INFO |       **Sugerencias:**
2025-01-28 10:30:36 | INFO |       - Incluir presupuestos para todas las licitaciones mencionadas
2025-01-28 10:30:36 | INFO |       - Añadir sección de requisitos técnicos de cada licitación
2025-01-28 10:30:36 | INFO |
2025-01-28 10:30:36 | INFO |       **Herramientas recomendadas por el revisor:**
2025-01-28 10:30:36 | INFO |       - get_tender_details: Obtener presupuesto y requisitos completos
2025-01-28 10:30:36 | INFO |         Parámetros sugeridos: {"tender_id": "001234-2025"}
2025-01-28 10:30:36 | INFO |
2025-01-28 10:30:36 | INFO |       **Validación de parámetros de tools ya ejecutadas:**
2025-01-28 10:30:36 | INFO |       - find_top_tenders - parámetro 'limit': Límite de 10 puede ser excesivo
2025-01-28 10:30:36 | INFO |         Valor sugerido: 5
2025-01-28 10:30:36 | INFO |
2025-01-28 10:30:36 | INFO |       **Feedback del revisor:**
2025-01-28 10:30:36 | INFO |       La respuesta está bien estructurada pero falta información crítica...
2025-01-28 10:30:36 | INFO |
2025-01-28 10:30:36 | INFO |       Genera tu respuesta mejorada:
```

*(El agente llama a get_tender_details como sugirió el revisor)*

```
2025-01-28 10:30:40 | INFO | --------------------------------------------------------------------------------
2025-01-28 10:30:40 | INFO | TOOL CALL: get_tender_details (Iteration 2)
2025-01-28 10:30:40 | INFO | --------------------------------------------------------------------------------
2025-01-28 10:30:40 | INFO | INPUT PARAMETERS:
2025-01-28 10:30:40 | INFO |   {
2025-01-28 10:30:40 | INFO |     "tender_id": "001234-2025"
2025-01-28 10:30:40 | INFO |   }
```

#### **Paso 5: Resumen Final**

```
2025-01-28 10:30:50 | INFO | ================================================================================
2025-01-28 10:30:50 | INFO | TOOL EXECUTION SUMMARY
2025-01-28 10:30:50 | INFO | ================================================================================
2025-01-28 10:30:50 | INFO | Total tools executed: 2
2025-01-28 10:30:50 | INFO |
2025-01-28 10:30:50 | INFO | Tool usage breakdown:
2025-01-28 10:30:50 | INFO |   - find_top_tenders: 1x
2025-01-28 10:30:50 | INFO |   - get_tender_details: 1x
2025-01-28 10:30:50 | INFO |
2025-01-28 10:30:50 | INFO | Detailed execution sequence:
2025-01-28 10:30:50 | INFO |
2025-01-28 10:30:50 | INFO |   1. ✓ find_top_tenders
2025-01-28 10:30:50 | INFO |      Parameters:
2025-01-28 10:30:50 | INFO |        {
2025-01-28 10:30:50 | INFO |          "query": "desarrollo software inteligencia artificial",
2025-01-28 10:30:50 | INFO |          "limit": 10
2025-01-28 10:30:50 | INFO |        }
2025-01-28 10:30:50 | INFO |      Result:
2025-01-28 10:30:50 | INFO |        - success: True
2025-01-28 10:30:50 | INFO |        - count: 3
2025-01-28 10:30:50 | INFO |        - document_ids: ['001234-2025', '002345-2025', '003456-2025']
2025-01-28 10:30:50 | INFO |
2025-01-28 10:30:50 | INFO |   2. ✓ get_tender_details
2025-01-28 10:30:50 | INFO |      Parameters:
2025-01-28 10:30:50 | INFO |        {
2025-01-28 10:30:50 | INFO |          "tender_id": "001234-2025"
2025-01-28 10:30:50 | INFO |        }
2025-01-28 10:30:50 | INFO |      Result:
2025-01-28 10:30:50 | INFO |        - success: True
2025-01-28 10:30:50 | INFO |        - document_id: 001234-2025
```

```
2025-01-28 10:30:51 | INFO | ================================================================================
2025-01-28 10:30:51 | INFO | ASSISTANT MESSAGE
2025-01-28 10:30:51 | INFO | ================================================================================
2025-01-28 10:30:51 | INFO | ## Licitación 001234-2025 - Desarrollo de Software IA
2025-01-28 10:30:51 | INFO |
2025-01-28 10:30:51 | INFO | **Organismo:** Ministerio de Economía
2025-01-28 10:30:51 | INFO | **Presupuesto:** €500,000
2025-01-28 10:30:51 | INFO | **Plazo de presentación:** 15/03/2025
2025-01-28 10:30:51 | INFO |
2025-01-28 10:30:51 | INFO | **Requisitos técnicos:**
2025-01-28 10:30:51 | INFO | - Experiencia mínima de 5 años en desarrollo de IA
2025-01-28 10:30:51 | INFO | - Conocimientos en Machine Learning y Deep Learning
2025-01-28 10:30:51 | INFO | ...
2025-01-28 10:30:51 | INFO |
2025-01-28 10:30:51 | INFO | METADATA:
2025-01-28 10:30:51 | INFO | {
2025-01-28 10:30:51 | INFO |   "documents": [
2025-01-28 10:30:51 | INFO |     {
2025-01-28 10:30:51 | INFO |       "id": "001234-2025",
2025-01-28 10:30:51 | INFO |       "title": "Desarrollo de Software IA",
2025-01-28 10:30:51 | INFO |       "budget_amount": 500000.0,
2025-01-28 10:30:51 | INFO |       "similarity_score": 0.89
2025-01-28 10:30:51 | INFO |     }
2025-01-28 10:30:51 | INFO |   ],
2025-01-28 10:30:51 | INFO |   "tools_used": ["find_top_tenders", "get_tender_details"],
2025-01-28 10:30:51 | INFO |   "iterations": 4,
2025-01-28 10:30:51 | INFO |   "review_tracking": {
2025-01-28 10:30:51 | INFO |     "review_performed": true,
2025-01-28 10:30:51 | INFO |     "max_loops": 3,
2025-01-28 10:30:51 | INFO |     "loops_executed": 1,
2025-01-28 10:30:51 | INFO |     "improvement_applied": true,
2025-01-28 10:30:51 | INFO |     "all_scores": [72, 89],
2025-01-28 10:30:51 | INFO |     "final_score": 89,
2025-01-28 10:30:51 | INFO |     "review_history": [
2025-01-28 10:30:51 | INFO |       {
2025-01-28 10:30:51 | INFO |         "loop": 1,
2025-01-28 10:30:51 | INFO |         "status": "NEEDS_IMPROVEMENT",
2025-01-28 10:30:51 | INFO |         "score": 72,
2025-01-28 10:30:51 | INFO |         "issues": ["Falta incluir el presupuesto...", "No se menciona ningún requisito..."],
2025-01-28 10:30:51 | INFO |         "suggestions": ["Incluir presupuestos...", "Añadir sección de requisitos..."]
2025-01-28 10:30:51 | INFO |       }
2025-01-28 10:30:51 | INFO |     ]
2025-01-28 10:30:51 | INFO |   }
2025-01-28 10:30:51 | INFO | }
```

---

## 🔍 Resumen de Hallazgos

### ✅ Lo que SÍ se está logueando correctamente:
1. **Mensajes del usuario** - completos
2. **Requests del agente principal al LLM** - incluyendo todos los mensajes y tools
3. **Responses del agente principal** - completas con metadatos
4. **Llamadas a tools** - con parámetros y resultados
5. **Resumen de ejecución de tools** - detallado
6. **Mensaje final del asistente** - con metadatos completos

### ⚠️ Lo que NO se está logueando (PROBLEMA):
1. **Prompt enviado al LLM Revisor** - no se registra
2. **Respuesta raw del LLM Revisor** - no se registra antes de parsearla
3. **Prompts de mejora** - se envían al agente pero no se registran explícitamente como "improvement prompt"

### 🛠️ Soluciones Necesarias:
1. Añadir logging en `ResponseReviewer.review_response()` para capturar:
   - Prompt completo enviado al revisor
   - Respuesta completa del revisor
2. Marcar claramente en los logs cuándo es un "improvement query"
3. Añadir metadatos de revisión en cada loop para transparencia completa

---

## 📊 Conclusión

El sistema de revisión está **bien diseñado** y **funcionalmente correcto**, pero le falta **transparencia completa en los logs** para el LLM Revisor.

**Recomendaciones:**
1. Implementar logging en `ResponseReviewer` similar al `ChatLogger`
2. Marcar explícitamente los "improvement loops" en los logs
3. Incluir timestamps de duración de cada loop
4. Añadir resumen final de todo el proceso de revisión

¿Quieres que implemente estas mejoras de logging ahora?
