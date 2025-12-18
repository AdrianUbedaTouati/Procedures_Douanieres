# 🔄 Flujo de Ejecución del Chat - TenderAI v3.7

**Sistema Function Calling con Review Loop Automático**

---

## 📋 Índice

1. [Visión General](#visión-general)
2. [Flujo Completo Paso a Paso](#flujo-completo-paso-a-paso)
3. [Review Loop en Detalle](#review-loop-en-detalle)
4. [Ejemplos Reales](#ejemplos-reales)

---

## Visión General

```
Usuario → Django → ChatAgentService → Agent (Iter 1) → ResponseReviewer → Agent (Iter 2) → Respuesta Final
                                            ↓                                    ↓
                                      Tools (16)                            Tools (16)
```

**Novedades v3.7:**
- ✅ Review Loop SIEMPRE ejecutado
- ✅ Segunda iteración automática con feedback
- ✅ Merge de resultados de ambas iteraciones
- ✅ Metadata de review tracking

**Llamadas mínimas:**
- 2 iteraciones de agent (inicial + mejorada)
- 1 llamada de review
- Total: 3+ llamadas LLM por mensaje

---

## Flujo Completo Paso a Paso

### 🎯 PASO 1: Usuario Envía Mensaje

**Archivo:** `chat/views.py` → `ChatMessageCreateView.post()`

```python
user_message_content = request.POST.get('message', '').strip()

# Crear mensaje en BD
user_message = ChatMessage.objects.create(
    session=session,
    role='user',
    content=user_message_content
)
```

**Logs:**
```
[CHAT REQUEST] Usuario: usuario@ejemplo.com (OPENAI)
[CHAT REQUEST] Sesión ID: 42
[CHAT REQUEST] Mensaje: Dame las mejores licitaciones de software
```

---

### 🎯 PASO 2: Preparar Historial

**Archivo:** `chat/views.py`

```python
# Obtener mensajes anteriores
previous_messages = session.messages.filter(
    created_at__lt=user_message.created_at
).order_by('created_at')

# Convertir a formato estándar
conversation_history = [
    {'role': msg.role, 'content': msg.content}
    for msg in previous_messages
]
```

---

### 🎯 PASO 3: ChatAgentService - ITERACIÓN INICIAL

**Archivo:** `chat/services.py` → `process_message()`

```python
# Crear agente
agent = FunctionCallingAgent(
    llm_provider=user.llm_provider,
    llm_model=user.openai_model,
    llm_api_key=user.llm_api_key,
    retriever=retriever,
    db_session=None,
    user=user
)

# ITERACIÓN 1: Ejecutar query inicial
result = agent.query(message, conversation_history)
response_content = result['answer']
```

**Logs:**
```
[SERVICE] Ejecutando query en el agente...
[SERVICE] Mensaje: Dame las mejores licitaciones de software
```

---

### 🎯 PASO 4: FunctionCallingAgent - ITERACIÓN 1

**Archivo:** `agent_ia_core/agent_function_calling.py`

**Loop de Function Calling:**
```python
for iteration in range(1, max_iterations + 1):  # max 15
    # 1. LLM decide tools
    response = self._call_llm_with_tools(messages)
    tool_calls = response.get('tool_calls', [])

    if not tool_calls:
        # Respuesta final
        break

    # 2. Ejecutar tools
    results = self.tool_registry.execute_tool_calls(tool_calls)

    # 3. Añadir resultados a mensajes
    # 4. Continuar loop
```

**Ejemplo ejecución:**
```
Iteración 1:
  LLM decide: search_tenders(query="software", limit=10)
  Tool ejecuta: 10 licitaciones encontradas

Iteración 2:
  LLM decide: get_company_info()
  Tool ejecuta: Perfil de empresa obtenido

Iteración 3:
  LLM genera respuesta final con ambos datos
  No tool_calls → FIN
```

**Resultado:**
```python
{
    'answer': "He encontrado 10 licitaciones de software...",
    'documents': [doc1, doc2, ...],
    'tools_used': ['search_tenders', 'get_company_info'],
    'iterations': 3
}
```

---

### 🎯 PASO 5: ResponseReviewer - REVISIÓN ⭐ NUEVO

**Archivo:** `chat/services.py` → `process_message()`

```python
# REVIEW LOOP (SIEMPRE ejecutado)
from chat.response_reviewer import ResponseReviewer

reviewer = ResponseReviewer(agent.llm)

review_result = reviewer.review_response(
    user_question=message,
    conversation_history=formatted_history,
    initial_response=response_content,
    metadata={
        'documents_used': result.get('documents', []),
        'tools_used': result.get('tools_used', []),
        'route': result.get('route', 'unknown')
    }
)
```

**Logs:**
```
[SERVICE] Iniciando revisión de respuesta...
[REVIEWER] Llamando al LLM revisor...
[REVIEWER] Revisión completada: NEEDS_IMPROVEMENT (score: 75/100)
```

**ResponseReviewer analiza:**

1. **FORMATO (30%):**
   - ¿Usa Markdown correctamente?
   - ¿Headers ## para cada licitación?
   - ¿Estructura clara?

2. **CONTENIDO (40%):**
   - ¿Responde completamente?
   - ¿Incluye presupuestos, plazos?
   - ¿Falta información?

3. **ANÁLISIS (30%):**
   - ¿Justifica por qué son las "mejores"?
   - ¿Usa datos objetivos?
   - ¿Es útil?

**Resultado del review:**
```python
{
    'status': 'NEEDS_IMPROVEMENT',  # o 'APPROVED'
    'score': 75,
    'issues': [
        'Falta justificación de por qué son las mejores',
        'No incluye análisis de fit con perfil de empresa'
    ],
    'suggestions': [
        'Agregar análisis de match con experiencia del usuario',
        'Incluir presupuestos y plazos de cada licitación'
    ],
    'feedback': 'La respuesta lista las licitaciones pero no explica por qué son las mejores para el usuario. Falta análisis personalizado.'
}
```

---

### 🎯 PASO 6: Segunda Iteración - MEJORA ⭐ SIEMPRE

**Archivo:** `chat/services.py` → `process_message()`

```python
# SIEMPRE ejecutar segunda iteración
print("[SERVICE] Ejecutando segunda iteración de mejora (siempre activo)...")

# Construir prompt de mejora
issues_list = '\n'.join([f"- {issue}" for issue in review_result['issues']])
suggestions_list = '\n'.join([f"- {sug}" for sug in review_result['suggestions']])

improvement_prompt = f"""Tu respuesta anterior fue revisada. Vamos a mejorarla.

**Tu respuesta original:**
{response_content}

**Problemas detectados:**
{issues_list if issues_list else '- Ningún problema grave detectado'}

**Sugerencias:**
{suggestions_list if suggestions_list else '- Mantener el buen formato actual'}

**Feedback del revisor:**
{review_result['feedback'] if review_result['feedback'] else 'La respuesta está bien estructurada, pero siempre podemos mejorarla.'}

**Tu tarea:**
Genera una respuesta MEJORADA que sea aún más completa y útil.

**IMPORTANTE:**
- Usa herramientas (tools) si necesitas buscar más información
- Si faltan datos específicos (presupuestos, plazos, etc.), búscalos
- Si el formato es incorrecto, corrígelo (usa ## para licitaciones múltiples)
- Si falta análisis, justifica tus recomendaciones con datos concretos

**Pregunta original del usuario:**
{message}

Genera tu respuesta mejorada:"""
```

**Ejecutar con historial extendido:**
```python
improvement_history = formatted_history + [
    {'role': 'user', 'content': message},
    {'role': 'assistant', 'content': response_content}
]

improved_result = agent.query(
    improvement_prompt,
    conversation_history=improvement_history
)
```

**Logs:**
```
[SERVICE] Ejecutando segunda iteración de mejora (siempre activo)...
[SERVICE] Ejecutando query de mejora...
```

**El agente en la 2da iteración:**
```
Iteración 1:
  LLM lee feedback
  LLM decide: get_tender_details(tender_id="00668461-2025")
            get_tender_details(tender_id="00677736-2025")
  Tools ejecutan: Detalles completos de 2 licitaciones

Iteración 2:
  LLM genera respuesta MEJORADA con:
    - Análisis personalizado basado en perfil
    - Presupuestos y plazos específicos
    - Justificación de por qué cada una es adecuada
    - Formato correcto con ##
  No tool_calls → FIN
```

**Resultado mejorado:**
```python
{
    'answer': """Basándome en tu perfil de empresa de desarrollo de software, te recomiendo:

## Desarrollo de plataforma ERP - ID: 00668461-2025

**Por qué es la más adecuada:**
- Presupuesto: 961,200 EUR - Ideal para empresas de tu tamaño
- Tu experiencia en desarrollo coincide con el CPV 72267100
- Plazo: 45 días restantes, tiempo suficiente para preparar propuesta

**Análisis de fit:**
- Match 95% con tu perfil
- Sector: Desarrollo de software (tu especialidad)
- Presupuesto adecuado para tu capacidad

## Sistema de gestión documental - ID: 00677736-2025

**Por qué es recomendable:**
- Presupuesto: 750,000 EUR
- Plazo: 30 días restantes
- Match 90% con tu experiencia

**Datos clave:**
- CPV: 72000000 (Software)
- Ubicación: ES300 (Madrid)
- Comprador: Autoridad Portuaria

[ID: 00668461-2025 | title]
[ID: 00677736-2025 | title]""",
    'documents': [doc1, doc2, doc3, doc4],  # Nuevos docs
    'tools_used': ['get_tender_details'],  # Nuevas tools
    'iterations': 2
}
```

---

### 🎯 PASO 7: Merge de Resultados

**Archivo:** `chat/services.py`

```python
# Update response con versión mejorada
response_content = improved_result.get('answer', response_content)

# Merge documents (evitar duplicados)
existing_doc_ids = {doc.get('ojs_notice_id') for doc in result.get('documents', [])}
new_docs = [
    doc for doc in improved_result.get('documents', [])
    if doc.get('ojs_notice_id') not in existing_doc_ids
]
result['documents'] = result.get('documents', []) + new_docs

# Merge tools used
result['tools_used'] = list(set(
    result.get('tools_used', []) + improved_result.get('tools_used', [])
))

# Update iterations count
result['iterations'] = result.get('iterations', 0) + improved_result.get('iterations', 0)
```

**Resultado final combinado:**
```python
{
    'answer': "[respuesta mejorada completa]",
    'documents': [doc1, doc2, doc3, doc4],  # Iter 1 + Iter 2
    'tools_used': ['search_tenders', 'get_company_info', 'get_tender_details'],
    'iterations': 5,  # 3 de iter1 + 2 de iter2
    'review': {
        'review_performed': True,
        'review_status': 'NEEDS_IMPROVEMENT',
        'review_score': 75,
        'review_issues': ['...'],
        'review_suggestions': ['...'],
        'improvement_applied': True
    }
}
```

---

### 🎯 PASO 8: Guardar en BD

**Archivo:** `chat/views.py`

```python
assistant_message = ChatMessage.objects.create(
    session=session,
    role='assistant',
    content=response['content'],  # Respuesta mejorada
    metadata={
        'route': response['metadata'].get('route'),
        'num_documents': len(documents_used),
        'tools_used': response['metadata'].get('tools_used'),
        'iterations': response['metadata'].get('iterations'),
        'total_tokens': cost_data['total_tokens'],
        'cost_eur': cost_data['total_cost_eur'],
        # Review tracking
        'review': response['metadata'].get('review')
    }
)
```

**Logs:**
```
[SERVICE] ✓ Respuesta mejorada generada: 850 caracteres
[SERVICE] ✓ Respuesta procesada: 850 caracteres
[SERVICE] Documentos recuperados: 4
[SERVICE] Herramientas usadas: search_tenders → get_company_info → get_tender_details
[SERVICE] Tokens totales: 1250 (in: 600, out: 650)
[SERVICE] Review - Status: NEEDS_IMPROVEMENT, Score: 75/100
[SERVICE] Review - Mejora aplicada (2da iteración ejecutada)
```

---

### 🎯 PASO 9: Respuesta al Frontend

**Archivo:** `chat/views.py`

```python
return JsonResponse({
    'success': True,
    'message': {
        'id': assistant_message.id,
        'content': assistant_message.content,
        'created_at': assistant_message.created_at.isoformat(),
        'role': 'assistant',
        'metadata': assistant_message.metadata
    }
})
```

**JSON enviado:**
```json
{
  "success": true,
  "message": {
    "id": 1234,
    "content": "Basándome en tu perfil de empresa...",
    "role": "assistant",
    "metadata": {
      "route": "function_calling",
      "num_documents": 4,
      "tools_used": ["search_tenders", "get_company_info", "get_tender_details"],
      "iterations": 5,
      "total_tokens": 1250,
      "cost_eur": 0.0125,
      "review": {
        "review_performed": true,
        "review_status": "NEEDS_IMPROVEMENT",
        "review_score": 75,
        "review_issues": ["Falta justificación..."],
        "review_suggestions": ["Agregar análisis..."],
        "improvement_applied": true
      }
    }
  }
}
```

---

## 🔄 Review Loop en Detalle

### Arquitectura del Review

```
┌─────────────────────────────────────────────────────────────────┐
│                    ITERACIÓN INICIAL                             │
│  Agent ejecuta tools → Genera respuesta → Retorna resultado     │
└────────────────────────────┬─────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    RESPONSEREVIEWER                              │
│                                                                  │
│  Input:                                                          │
│  - user_question: "Dame las mejores licitaciones de software"  │
│  - conversation_history: [...]                                  │
│  - initial_response: "He encontrado 10 licitaciones..."        │
│  - metadata: {documents, tools_used, route}                     │
│                                                                  │
│  Proceso:                                                        │
│  1. Construir prompt de revisión con criterios                 │
│  2. Llamar LLM con prompt                                       │
│  3. Parsear respuesta (STATUS, SCORE, ISSUES, SUGGESTIONS)     │
│  4. Retornar análisis estructurado                              │
│                                                                  │
│  Output:                                                         │
│  {                                                               │
│    status: 'NEEDS_IMPROVEMENT',                                 │
│    score: 75,                                                    │
│    issues: [...],                                                │
│    suggestions: [...],                                           │
│    feedback: "..."                                               │
│  }                                                               │
└────────────────────────────┬─────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│               SEGUNDA ITERACIÓN (SIEMPRE)                        │
│                                                                  │
│  Prompt mejorado:                                                │
│  "Tu respuesta: [...]                                            │
│   Problemas: [...]                                               │
│   Sugerencias: [...]                                             │
│   Feedback: [...]                                                │
│                                                                  │
│   Genera respuesta MEJORADA con acceso a tools"                │
│                                                                  │
│  Agent ejecuta con tools completos → Respuesta mejorada         │
└────────────────────────────┬─────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    MERGE Y RETORNO                               │
│  - Response final = respuesta mejorada                           │
│  - Documents = iter1 + iter2                                     │
│  - Tools = union de ambas                                        │
│  - Metadata incluye review tracking                              │
└──────────────────────────────────────────────────────────────────┘
```

### Criterios de Evaluación

**Prompt del ResponseReviewer:**
```
Analiza la respuesta y evalúa:

1. FORMATO (30 puntos):
   - ¿Usa Markdown correctamente?
   - Si hay múltiples licitaciones, ¿usa ## para cada una?
   - ¿Está bien estructurado y legible?

2. CONTENIDO (40 puntos):
   - ¿Responde completamente a la pregunta?
   - ¿Incluye todos los datos relevantes (IDs, presupuestos, plazos)?
   - ¿Falta información importante?

3. ANÁLISIS (30 puntos):
   - Si pidió recomendaciones, ¿justifica con datos?
   - ¿Usa los documentos consultados correctamente?
   - ¿Es útil y profesional?

Responde en formato:
STATUS: [APPROVED o NEEDS_IMPROVEMENT]
SCORE: [0-100]
ISSUES: [lista]
SUGGESTIONS: [lista]
FEEDBACK: [explicación específica]
```

### Decisión: SIEMPRE Mejorar

**Por qué SIEMPRE se ejecuta la segunda iteración:**
- ✅ Incluso respuestas "APPROVED" pueden mejorarse
- ✅ El revisor siempre proporciona sugerencias constructivas
- ✅ La segunda iteración puede agregar más contexto
- ✅ Garantiza máxima calidad en todas las respuestas
- ✅ El usuario solicitó este comportamiento explícitamente

---

## 📊 Ejemplos Reales

### Ejemplo 1: Consulta Simple → Review → Mejora

**Input:** "Dame licitaciones de IT"

**Iteración 1:**
- Tools: `search_tenders(query="IT", limit=10)`
- Respuesta: "He encontrado 10 licitaciones de IT..."
- Formato: Lista numerada 1, 2, 3...

**Review:**
- Status: NEEDS_IMPROVEMENT
- Score: 65/100
- Issue: "Usa lista numerada en vez de headers ##"
- Suggestion: "Usar ## para cada licitación"

**Iteración 2 (mejora):**
- Lee feedback
- No usa tools adicionales
- Reformatea con ## para cada licitación
- Respuesta mejorada con formato correcto

**Resultado:** Mismos datos, mejor formato

---

### Ejemplo 2: Consulta Compleja → Review → Búsqueda Adicional

**Input:** "Cuáles son las mejores licitaciones para mi empresa?"

**Iteración 1:**
- Tools: `search_tenders(query="licitaciones", limit=10)`
- Respuesta: "Encontré 10 licitaciones..."
- Issue: No usa perfil de empresa

**Review:**
- Status: NEEDS_IMPROVEMENT
- Score: 70/100
- Issue: "Falta análisis personalizado"
- Suggestion: "Usar get_company_info() para contexto"

**Iteración 2 (mejora):**
- Tools: `get_company_info()`, `get_tender_details(id1)`, `get_tender_details(id2)`
- Genera análisis de match basado en perfil
- Explica por qué cada licitación es adecuada
- Respuesta con análisis completo

**Resultado:** Más documentos, mejor análisis

---

### Ejemplo 3: Respuesta Correcta → Review → Refinamiento

**Input:** "Presupuesto de licitación 00668461-2025"

**Iteración 1:**
- Tools: `get_tender_details(tender_id="00668461-2025")`
- Respuesta: "El presupuesto es 961,200 EUR"
- Formato: Correcto

**Review:**
- Status: APPROVED
- Score: 85/100
- Issue: Ninguno
- Suggestion: "Agregar contexto (comprador, plazo)"

**Iteración 2 (mejora):**
- No usa tools adicionales (ya tiene los datos)
- Agrega información de contexto
- Respuesta: "El presupuesto es 961,200 EUR. Comprador: Fundación Estatal. Plazo: 45 días restantes."

**Resultado:** Respuesta más completa

---

## ⚙️ Configuración

**Variables relevantes en .env:**
```bash
# LLM Settings
LLM_PROVIDER=openai
LLM_TEMPERATURE=0.3

# Iteraciones
MAX_ITERATIONS=15

# Review (siempre activo, no configurable)
```

**User model:**
```python
llm_provider = 'openai'
openai_model = 'gpt-4o-mini'
llm_api_key = 'sk-...'
```

---

## 📊 Métricas

### Tokens Consumidos (ejemplo)

| Etapa | Tokens In | Tokens Out | Total |
|-------|-----------|------------|-------|
| Iteración 1 (3 ciclos) | 400 | 250 | 650 |
| Review | 150 | 100 | 250 |
| Iteración 2 (2 ciclos) | 350 | 200 | 550 |
| **TOTAL** | **900** | **550** | **1450** |

### Latencia (ejemplo con OpenAI)

| Etapa | Tiempo |
|-------|--------|
| Iteración 1 | 1.2s |
| Review | 0.4s |
| Iteración 2 | 0.9s |
| Merge + BD | 0.1s |
| **TOTAL** | **2.6s** |

---

## 🔗 Referencias

- **Arquitectura**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Tools**: [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md)
- **Configuración**: [CONFIGURACION_AGENTE.md](CONFIGURACION_AGENTE.md)

---

**Versión**: 3.7.0
**Última actualización**: 2025-01-19
**Feature destacada**: Review Loop automático SIEMPRE activo

**🤖 Generated with [Claude Code](https://claude.com/claude-code)**

**Co-Authored-By: Claude <noreply@anthropic.com>**
