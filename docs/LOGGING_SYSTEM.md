# Sistema de Logging Mejorado - TenderAI Platform

**Versión:** 3.7.2
**Fecha:** 2025-11-27

## Descripción General

El sistema de logging de TenderAI Platform ha sido mejorado para proporcionar trazabilidad completa de todas las operaciones del agente de IA, incluyendo:

- ✅ Llamadas a funciones (tools) con parámetros completos
- ✅ Resultados de cada función con estado de éxito/fallo
- ✅ Orden secuencial de ejecución
- ✅ Flujo de decisiones del LLM en cada iteración
- ✅ Resumen de herramientas utilizadas
- ✅ Contexto completo de conversación

## Ubicación de Logs

Los logs se almacenan en directorios específicos según su tipo:

```
logs/
├── chat/           # Logs de conversaciones (MEJORADO)
├── indexacion/     # Logs de indexación de XMLs
└── obtener/        # Logs de descarga de licitaciones
```

### Formato de Archivos de Chat

```
logs/chat/session_{session_id}_{timestamp}.log
```

Ejemplo: `logs/chat/session_42_20251127_143022.log`

## Estructura de Log de Chat

Cada sesión de chat registra:

### 1. Mensaje del Usuario
```
================================================================================
USER MESSAGE (session 42)
================================================================================
¿Cuál es la licitación más cara?
```

### 2. Request al LLM
```
================================================================================
LLM REQUEST → google/gemini-2.0-flash-exp
================================================================================
MESSAGES:
  [0] Role: system
      Eres un asistente experto en licitaciones públicas europeas...
  [1] Role: user
      ¿Cuál es la licitación más cara?

TOOLS AVAILABLE:
  [0] search_tenders
      Description: Busca licitaciones por contenido/tema
  [1] find_by_budget
      Description: Filtra licitaciones por rango de presupuesto
  ...
```

### 3. Flujo de Ejecución por Iteración
```
================================================================================
ITERATION 1 - EXECUTION FLOW
================================================================================
LLM Decision: Call 1 tool(s)
Tools Called: get_statistics
```

### 4. Llamada a Tool (con parámetros)
```
--------------------------------------------------------------------------------
TOOL CALL: get_statistics (Iteration 1)
--------------------------------------------------------------------------------
INPUT PARAMETERS:
  {
    "metric": "max_budget"
  }
```

### 5. Resultado de Tool (con estado)
```
--------------------------------------------------------------------------------
TOOL RESULT: get_statistics [✓ SUCCESS] (Iteration 1)
--------------------------------------------------------------------------------
  {
    "success": true,
    "data": {
      "metric": "max_budget",
      "value": 15000000.0,
      "tender_id": "754920-2025",
      "tender_title": "Construcción de infraestructura ferroviaria"
    }
  }
```

### 6. Iteraciones Subsiguientes
El agente puede hacer múltiples iteraciones, cada una con su propio flujo de ejecución:

```
================================================================================
ITERATION 2 - EXECUTION FLOW
================================================================================
LLM Decision: Call 1 tool(s)
Tools Called: get_tender_details

--------------------------------------------------------------------------------
TOOL CALL: get_tender_details (Iteration 2)
--------------------------------------------------------------------------------
INPUT PARAMETERS:
  {
    "tender_id": "754920-2025"
  }

--------------------------------------------------------------------------------
TOOL RESULT: get_tender_details [✓ SUCCESS] (Iteration 2)
--------------------------------------------------------------------------------
  {
    "success": true,
    "tender": {
      "id": "754920-2025",
      "title": "Construcción de infraestructura ferroviaria",
      "budget": 15000000.0,
      "deadline": "2025-03-15",
      ...
    }
  }
```

### 7. Respuesta Final del LLM
```
================================================================================
LLM RESPONSE ←
================================================================================
{
  "answer": "La licitación más cara es la 754920-2025 con un presupuesto de €15,000,000...",
  "tools_used": ["get_statistics", "get_tender_details"],
  "iterations": 2,
  ...
}
```

### 8. Resumen de Ejecución de Tools
```
================================================================================
TOOL EXECUTION SUMMARY
================================================================================
Total tools executed: 2

Tool usage breakdown:
  - get_statistics: 1x
  - get_tender_details: 1x

Execution sequence:
  1. ✓ get_statistics
  2. ✓ get_tender_details
================================================================================
```

### 9. Mensaje Final del Asistente
```
================================================================================
ASSISTANT MESSAGE
================================================================================
La licitación más cara es la 754920-2025: "Construcción de infraestructura
ferroviaria" con un presupuesto de €15,000,000. La fecha límite para presentar
ofertas es el 15 de marzo de 2025...

METADATA:
  {
    "provider": "google",
    "route": "function_calling",
    "documents_used": [...],
    "tools_used": ["get_statistics", "get_tender_details"],
    "iterations": 2,
    "total_tokens": 1247,
    "cost_eur": 0.0023
  }
```

## Mejoras Implementadas

### Antes (v3.7.1)
- ❌ Solo se registraban mensajes básicos
- ❌ No se registraban parámetros de tools
- ❌ No se registraban resultados de tools
- ❌ No había trazabilidad del flujo de ejecución
- ❌ Difícil depurar problemas

### Ahora (v3.7.2)
- ✅ Registro completo de todos los parámetros de entrada
- ✅ Registro completo de todos los resultados
- ✅ Indicadores de éxito/fallo por tool
- ✅ Flujo de ejecución por iteración
- ✅ Resumen ejecutivo de tools usadas
- ✅ Trazabilidad completa para debugging

## Casos de Uso

### 1. Debugging de Tools Fallidas
Si una tool falla, puedes ver exactamente:
- Qué parámetros se enviaron
- Qué error retornó
- En qué iteración falló

```
--------------------------------------------------------------------------------
TOOL RESULT: search_tenders [✗ FAILED] (Iteration 1)
--------------------------------------------------------------------------------
  {
    "success": false,
    "error": "No documents found in ChromaDB",
    "suggestion": "Run vectorization first"
  }
```

### 2. Optimización de Prompts
Puedes ver qué tools se llamaron innecesariamente:

```
Tool usage breakdown:
  - search_tenders: 3x     ← Demasiadas búsquedas
  - get_statistics: 1x
  - get_tender_details: 5x ← Demasiadas consultas
```

### 3. Análisis de Costos
Cada iteración registra tokens y costos:

```
METADATA:
  "total_tokens": 2547,
  "cost_eur": 0.0045
```

### 4. Auditoría de Decisiones
Puedes ver exactamente qué decidió el LLM en cada paso:

```
ITERATION 1 - EXECUTION FLOW
LLM Decision: Call 2 tool(s)
Tools Called: search_tenders, get_statistics
```

## Componentes Técnicos

### 1. ChatLogger (apps/core/logging_config.py)

Nuevos métodos añadidos:

```python
def log_tool_call(self, tool_name: str, tool_input: Dict[str, Any], iteration: int = None)
def log_tool_result(self, tool_name: str, result: Any, iteration: int = None, success: bool = True)
def log_execution_flow(self, iteration: int, decision: str, tools_called: list)
def log_tool_execution_summary(self, tools_history: list)
```

### 2. FunctionCallingAgent (agent_ia_core/agent_function_calling.py)

Modificado para integrar el logger:

```python
def __init__(self, ..., chat_logger=None):
    self.chat_logger = chat_logger

def query(self, question: str, conversation_history: Optional[List[Dict]] = None):
    # Log automático en iteration 0
    if self.chat_logger:
        self.chat_logger.log_tool_call('get_tenders_summary', {'limit': 20}, iteration=0)

    # Log en cada iteración
    while iteration < self.max_iterations:
        if self.chat_logger:
            self.chat_logger.log_execution_flow(iteration, decision, tools_to_call)

        # Ejecutar tools y log
        for result in results:
            if self.chat_logger:
                self.chat_logger.log_tool_call(tool_name, tool_args, iteration=iteration)
                self.chat_logger.log_tool_result(tool_name, tool_result, iteration=iteration, success=success)
```

### 3. ChatAgentService (apps/chat/services.py)

Pasa el logger al agente:

```python
self._agent = FunctionCallingAgent(
    ...,
    chat_logger=self.chat_logger  # Pasar logger para logging detallado
)
```

## Formato de Timestamp

Todos los logs usan el formato:
```
%Y-%m-%d %H:%M:%S
```

Ejemplo: `2025-11-27 14:30:22`

## Tamaño de Logs

Los logs pueden crecer significativamente con conversaciones largas:

- **Conversación simple (1 mensaje):** ~5 KB
- **Conversación con 3-4 tools:** ~20 KB
- **Conversación compleja (múltiples iteraciones):** ~100 KB

**Recomendación:** Implementar rotación de logs si el uso es intensivo.

## Rotación de Logs (Futura Implementación)

Para producción, considerar:

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    self.log_file,
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5,
    encoding='utf-8'
)
```

## Privacidad y Seguridad

⚠️ **IMPORTANTE:** Los logs contienen:
- Mensajes completos del usuario
- Contenido de licitaciones
- Información de la empresa del usuario

**Recomendaciones:**
1. Proteger el directorio `logs/` con permisos restrictivos
2. No compartir logs sin anonimizar datos sensibles
3. Implementar política de retención (ej: borrar logs > 30 días)

## Sistema de Logging de Búsqueda Iterativa

### v3.8.0 (2025-12-02)

A partir de esta versión, el sistema incluye logging completo para búsquedas iterativas con verificación de contenido (5 búsquedas secuenciales).

#### Nuevos Métodos en ChatLogger

**1. log_iterative_search_start(query, mode, limit, context)**
- Registra inicio de búsqueda iterativa
- **Simple**: Query, modo, límite, contexto disponible (empresa, historial, tools previas)
- **Detallado**: JSON completo del contexto

**2. log_search_iteration_start(iteration, total)**
- Marca inicio de cada iteración (1/5, 2/5, etc.)

**3. log_query_optimization(iteration, optimized_query, llm_request, llm_response)**
- Registra query optimizada generada por LLM intermediario
- **Simple**: Query optimizada (primeros 150 caracteres)
- **Detallado**: Prompt completo + respuesta raw del LLM

**4. log_semantic_search(iteration, query, k, results)**
- Registra búsqueda semántica en ChromaDB
- **Simple**: Query, top-K, resultado (doc_id + chunk_count)
- **Detallado**: JSON completo de resultados

**5. log_document_retrieval(iteration, doc_id, retrieval_result)**
- Registra obtención de documento completo via get_tender_details
- **Simple**: doc_id, status, título, comprador, presupuesto
- **Detallado**: JSON completo del documento

**6. log_content_verification(iteration, doc_id, verification_request, verification_response, parsed_analysis)**
- Registra verificación de contenido por LLM
- **Simple**: doc_id, corresponds (bool), score 0-10, reasoning (primeros 100 caracteres)
- **Detallado**:
  - Prompt completo enviado al LLM verificador
  - Respuesta raw del LLM
  - Análisis parseado (corresponds, score, reasoning, missing_info)

**7. log_iteration_feedback(iteration, feedback, next_iteration)**
- Registra feedback dado al LLM para próxima iteración
- **Simple**: Feedback (primeros 150 caracteres)
- **Detallado**: Feedback completo

**8. log_iteration_result(iteration, result)**
- Registra resultado completo de una iteración
- **Simple**: doc_id, chunk_count, reliability, corresponds, llm_score
- **Detallado**: JSON completo del resultado

**9. log_final_selection(selection_request, selection_response, final_analysis, selected_documents)**
- Registra análisis final y selección de documentos
- **Simple**: Documentos seleccionados, confianza, fiabilidad, reasoning (primeros 200 caracteres)
- **Detallado**:
  - Prompt completo enviado al LLM selector
  - Respuesta raw del LLM
  - Análisis parseado (selected_ids, reasoning, is_reliable, confidence)
  - Lista de documentos seleccionados

**10. log_iterative_search_end(total_iterations, success, analysis, documents_found)**
- Registra fin de búsqueda iterativa
- **Simple**: Status, iteraciones totales, documentos encontrados, confianza, fiabilidad
- **Detallado**: JSON completo del análisis final

**11. log_fallback_search(reason, fallback_result)**
- Registra cuando se usa búsqueda de respaldo
- **Simple**: Razón, documentos encontrados
- **Detallado**: JSON completo del resultado de fallback

#### Ejemplo de Log de Búsqueda Iterativa

```
================================================================================
🔍 ITERATIVE SEARCH START - Mode: single
================================================================================
Original query: licitaciones de desarrollo de software con IA
Target documents: 1
Company info available: True
Conversation history: 3 messages
Tool calls history: 2 calls

--------------------------------------------------------------------------------
📍 SEARCH ITERATION 1/5
--------------------------------------------------------------------------------

🧠 Query Optimization (Iteration 1)
Optimized query: desarrollo software inteligencia artificial machine learning deep learning
Query length: 85 characters

🔎 Semantic Search (Iteration 1)
Query: desarrollo software inteligencia artificial...
Top-K: 7
Result: 00123456-2025 (3 chunks)

📄 Document Retrieval (Iteration 1)
Document ID: 00123456-2025
Status: ✓ SUCCESS
Title: Desarrollo de Sistema de IA para Análisis de Datos
Buyer: Ministerio de Economía
Budget: 500000.0 EUR

✓ Content Verification (Iteration 1)
Document: 00123456-2025
Corresponds: True
LLM Score: 9/10
Reasoning: El documento corresponde perfectamente a la búsqueda. Incluye desarrollo de software con IA...

📊 Iteration 1 Result Summary
Document: 00123456-2025
Chunks: 3
Reliability: MUY FIABLE
Corresponds: True
LLM Score: 9/10

💬 Feedback for Next Iteration (→ 2)
Feedback: ✓ Buen resultado. Mejor documento hasta ahora: 00123456-2025 (9/10)
Genera query para BÚSQUEDA 2/5 con un enfoque diferente.

... (iteraciones 2-5) ...

================================================================================
🎯 FINAL SELECTION
================================================================================
Documents selected: 1
Confidence: 0.95
Is reliable: True
Reasoning: Documento 00123456-2025 apareció en 3 de 5 búsquedas con puntuaciones altas...

================================================================================
🏁 ITERATIVE SEARCH END
================================================================================
Status: ✓ SUCCESS
Total iterations: 5
Documents found: 1
Unique documents: 3
Confidence: 0.95
Is reliable: True
```

#### Integración con search_base.py

La función `optimize_and_search_iterative_with_verification()` acepta un parámetro opcional `chat_logger` que se inyecta automáticamente desde el ToolRegistry cuando se ejecutan `find_best_tender` o `find_top_tenders`.

```python
# En find_best_tender.py
search_result = optimize_and_search_iterative_with_verification(
    original_query=query,
    conversation_history=conversation_history,
    tool_calls_history=tool_calls_history,
    company_info=company_info,
    vectorstore=retriever,
    llm=llm,
    user=user,
    mode="single",
    chat_logger=chat_logger  # ← Inyectado automáticamente
)
```

---

## Changelog

### v3.8.0 (2025-12-02)
- ✨ Añadidos 11 métodos de logging para búsqueda iterativa
- ✨ Logging completo de prompts del LLM intermediario
- ✨ Logging de verificación de contenido con análisis completo
- ✨ Logging de selección final con justificación del LLM
- ✨ Doble archivo: simple (conciso) + detallado (JSON completo)
- 📝 Documentación completa de nuevos métodos

### v3.7.2 (2025-11-27)
- ✨ Añadido logging detallado de tool calls con parámetros
- ✨ Añadido logging de resultados con estado éxito/fallo
- ✨ Añadido logging de flujo de ejecución por iteración
- ✨ Añadido resumen de tools ejecutadas
- ✨ Integración completa con FunctionCallingAgent
- 📝 Documentación completa del sistema de logging

### v3.7.1 (2025-11-26)
- Logging básico de mensajes y respuestas LLM

## Ejemplo Completo de Log

Ver archivo de ejemplo en: `docs/examples/chat_log_example.log`

## Soporte

Para problemas con el sistema de logging:
1. Verificar permisos del directorio `logs/`
2. Verificar que ChatLogger se inicializa con session_id
3. Verificar que el logger se pasa al FunctionCallingAgent
4. Revisar que las tools retornan formato `{'success': bool, ...}`
