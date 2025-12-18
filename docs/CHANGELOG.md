# Changelog - TenderAI Platform

## [v3.8.0] - 2025-12-02

### Sistema de Búsqueda Iterativa con Verificación de Contenido
- **5 búsquedas secuenciales optimizadas** con LLM intermediario:
  - ✅ Cada búsqueda usa query optimizada por LLM considerando resultados previos
  - ✅ Verificación de contenido completo (no solo chunks)
  - ✅ Análisis de correspondencia real con puntuación 0-10
  - ✅ Feedback iterativo para mejorar búsquedas siguientes
- **find_best_tender**: Retorna LA mejor licitación (singular)
  - Selección basada en chunk_count + puntuación LLM + apariciones múltiples
- **find_top_tenders**: Retorna X mejores licitaciones (plural)
  - Selección iterativa con eliminación de duplicados
  - Máximo 10 documentos únicos

### Sistema de Logging Completo para Búsqueda Iterativa
- **11 nuevos métodos en ChatLogger** (doble archivo: simple + detallado):
  - `log_iterative_search_start()` - Inicio con contexto completo
  - `log_search_iteration_start()` - Inicio de cada búsqueda
  - `log_query_optimization()` - Query optimizada por LLM
  - `log_semantic_search()` - Resultados de ChromaDB
  - `log_document_retrieval()` - Documento completo via get_tender_details
  - `log_content_verification()` - Análisis de correspondencia por LLM
  - `log_iteration_feedback()` - Feedback para próxima búsqueda
  - `log_iteration_result()` - Resultado completo de iteración
  - `log_final_selection()` - Selección final con análisis LLM
  - `log_iterative_search_end()` - Fin con métricas completas
  - `log_fallback_search()` - Búsqueda de respaldo si falla sistema
- **Integración completa** en `search_base.py`:
  - Logging de prompts completos del LLM intermediario
  - Logging de respuestas raw antes de parsear
  - Logging de verificación de contenido con análisis completo

### Fix Metadata de Contacto en Chunks
- **Problema detectado**: Campos de contacto faltantes en chunks 2-4
  - `chunking.py`: Modificado `_extract_common_metadata()` para extraer contact_email, contact_phone, contact_url, contact_fax
  - `index_build.py`: Modificado `_chunks_to_documents()` para indexar campos de contacto
- **Resultado**: Metadata completa en TODOS los chunks (0-4)
- **Script de verificación**: `verify_metadata_fix.py`

### Documentación Completa
- **ANALISIS_REVISION_DETALLADO.md**: Análisis exhaustivo del sistema de revisión
  - Flujo completo con diagramas
  - Prompts completos del revisor y de mejora
  - Detalles técnicos de todos los parámetros
  - Ejemplo de ejecución completa con logs
- **LOGGING_SYSTEM.md**: Documentación del sistema de logging dual
- **CHANGELOG.md**: Actualizado con últimas mejoras

### Beneficios
- 🎯 **Mejor precisión**: Verificación de contenido real, no solo similitud semántica
- 🔍 **Transparencia total**: Logging completo de todas las decisiones del LLM
- 📊 **Métricas detalladas**: Confianza, fiabilidad, apariciones, progresión de chunks
- 💡 **Justificación objetiva**: LLM explica por qué seleccionó cada documento
- ✅ **Metadata completa**: Todos los campos de contacto en todos los chunks

---

## [v3.7.2] - 2025-11-27

### Sistema de Logging Mejorado
- **Trazabilidad completa** de tool calls:
  - ✅ Logging detallado de parámetros de entrada por tool
  - ✅ Logging de resultados con indicadores de éxito/fallo (✓/✗)
  - ✅ Logging de flujo de ejecución por iteración
  - ✅ Resumen ejecutivo de todas las tools ejecutadas
- **Nuevos métodos en ChatLogger**:
  - `log_tool_call()` - Registra llamada con parámetros e iteración
  - `log_tool_result()` - Registra resultado con estado de éxito
  - `log_execution_flow()` - Registra decisión del LLM en cada iteración
  - `log_tool_execution_summary()` - Resumen final de tools usadas
- **Integración con FunctionCallingAgent**:
  - Logger pasado como parámetro opcional `chat_logger`
  - Logging automático en cada iteración del loop
  - Tracking de tool calls múltiples por iteración

### Documentación
- **docs/LOGGING_SYSTEM.md**: Guía completa del sistema de logging
  - Estructura detallada de logs
  - Casos de uso (debugging, optimización, auditoría)
  - Ejemplos reales con formato visual
- **docs/examples/chat_log_example.log**: Ejemplo completo de log con múltiples iteraciones

### Beneficios
- 🔍 **Debugging mejorado**: Ver exactamente qué falló y por qué
- 📊 **Análisis de uso**: Identificar tools más usadas y patrones
- 💰 **Tracking de costos**: Tokens y costos por iteración
- 🔒 **Auditoría completa**: Registro de todas las decisiones del LLM

---

## [v3.7.1] - 2025-11-21

### Reestructuracion de agent_ia_core
- **Nueva estructura modular** con carpetas organizadas:
  - `parser/` - XML parsing y chunking (xml_parser.py, chunking.py, tools_xml.py)
  - `prompts/` - System prompts del agente
  - `indexing/` - RAG retrieval e indexacion (retriever.py, index_build.py, ingest.py)
  - `download/` - Descarga TED (descarga_xml.py, token_tracker.py)
  - `engines/` - Motores especializados (recommendation_engine.py)
- **Todos los imports actualizados** en apps/, tests/, y tools/

### Correcciones
- **Fix web_search**: Ahora busca realmente en internet (antes mostraba datos inventados)
  - Agregada tool web_search al system prompt del agente
- **Fix LOGS_DIR**: Los logs ahora se crean en la carpeta raiz del proyecto
- **Fix TenderAI.settings**: Todas las referencias cambiadas a config.settings
- **Fix static files**: Restaurado Dark Mode CSS que se habia perdido en refactoring

### Documentacion
- README.md movido a la raiz del proyecto
- Actualizada estructura de proyecto con nueva organizacion
- Agregada tabla de almacenamiento (donde se guarda cada cosa)

---

## [v3.7.0] - 2025-11-15

### BrowseInteractiveTool con Playwright
- **Navegador Chromium headless** con Playwright
- **JavaScript completo** (SPA, React, Vue, Angular)
- **Modo inteligente con LLM**: Analiza pagina -> Decide accion -> Ejecuta -> Repite
- **Acciones soportadas**: Click, fill forms, wait, scroll, navigate
- **95-98% success rate** en sitios gubernamentales

---

## [v3.6.0] - 2025-11-10

### Review Loop Automatico
- **ResponseReviewer** evalua TODAS las respuestas
- **3 criterios**: Formato (30%), Contenido (40%), Analisis (30%)
- **Segunda iteracion SIEMPRE ejecutada** con prompt mejorado
- **Merge inteligente** de documentos de ambas iteraciones

---

## [v3.0.0] - 2025-10-01

### Sistema Function Calling Completo
- **16 tools especializadas** (11 activas + 5 opcionales)
- **Hasta 15 iteraciones automaticas**
- **SchemaConverter** para multi-proveedor LLM
- **ToolRegistry** con categorias: Context, Search, Info, Analysis, Quality, Web

---

## [v1.4.0] - 2025-09-15

### Routing per-message + Ollama
- **100% local** con Ollama (sin API keys)
- **Routing LLM** per-message

---

## [v1.3.0] - 2025-09-01

### Descarga TED mejorada
- **Cancelacion en tiempo real**
- **Precarga automatica** de perfil de empresa
- **Correccion filtros CPV** multiples

---

## [v1.2.0] - 2025-08-15

### Recomendaciones IA Multicriteria
- **Motor de recomendaciones** con 5 dimensiones
- Score tecnico, presupuesto, geografico, experiencia, competencia

---

## [v1.1.0] - 2025-08-01

### Descarga TED inicial
- **Integracion TED API**
- **Progreso en tiempo real** con SSE

---

## [v1.0.0] - 2025-07-15

### Lanzamiento inicial
- Sistema de autenticacion
- Perfiles de empresa
- Chat RAG basico
- Gestion de licitaciones
