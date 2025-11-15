# 📚 Índice de Documentación - TenderAI v3.7

**Sistema de Function Calling con Review Loop Automático y Navegación Web Interactiva**

---

## 🎯 Empezar Aquí

Si es tu primera vez, lee en este orden:

1. **[README.md](README.md)** ← Empieza aquí
   - Visión general del proyecto
   - Instalación y configuración
   - Guía de uso rápida
   - Comparación de proveedores LLM

2. **[TOOLS_REFERENCE.md](TOOLS_REFERENCE.md)** ← Lee esto segundo
   - Documentación completa de las **16 tools** (11 activas + 5 opcionales)
   - Ejemplos de uso para cada tool
   - Casos de uso típicos
   - Categorización: Context, Search, Info, Analysis, Quality, Web

3. **[ARCHITECTURE.md](ARCHITECTURE.md)** ← Lee esto para entender el sistema
   - Arquitectura de alto nivel
   - Componentes principales
   - Flujo de datos completo
   - Integración entre componentes

---

## 📖 Documentación Principal

### 🏠 **README.md**

**Qué contiene:**
- Características principales del sistema
- Requisitos e instalación
- Configuración de proveedores (Ollama, OpenAI, Gemini)
- Guía de uso paso a paso
- Solución de problemas
- Roadmap

**Cuándo leerlo:**
- Primera vez usando el sistema
- Instalación en un nuevo entorno
- Configuración de un nuevo proveedor LLM

---

### 🛠️ **TOOLS_REFERENCE.md**

**Qué contiene:**
- Documentación completa de las **16 tools**:
  - **Context (2)**: `get_company_info`, `get_tenders_summary`
  - **Search (5)**: `search_tenders`, `find_by_budget`, `find_by_deadline`, `find_by_cpv`, `find_by_location`
  - **Info (2)**: `get_tender_details`, `get_tender_xml`
  - **Analysis (2)**: `get_statistics`, `compare_tenders`
  - **Quality (2, opcional)**: `grade_documents`, `verify_fields`
  - **Web (3, opcional)**: `web_search`, `browse_webpage`, `browse_interactive` ⭐ NUEVO v3.7
- Parámetros de cada tool
- Ejemplos de uso
- Respuestas esperadas
- Casos de uso típicos
- Activación de tools opcionales

**Cuándo leerlo:**
- Quieres entender qué puede hacer el sistema
- Necesitas saber qué tool usar para un caso específico
- Estás desarrollando nuevas features
- Debugging de consultas

**Ejemplos que encontrarás:**
```
Usuario: "Busca licitaciones de IT con presupuesto > 50k"
→ Tools: find_by_cpv("IT") + find_by_budget(min_budget=50000)

Usuario: "Compara licitaciones 123 y 456"
→ Tools: compare_tenders(tender_ids=["123", "456"])
```

---

### 🏗️ **ARCHITECTURE.md**

**Qué contiene:**
- Arquitectura de alto nivel v3.7
- Componentes principales:
  - FunctionCallingAgent (max 15 iteraciones)
  - ToolRegistry (16 tools)
  - ResponseReviewer ⭐ NUEVO v3.6 (Review Loop)
  - SchemaConverter (multi-proveedor)
  - ChatAgentService (con Review Loop automático)
  - Retriever (ChromaDB con embeddings especializados)
  - BrowseInteractiveTool ⭐ NUEVO v3.7 (Playwright)
- Flujo de datos completo con Review Loop
- Comparación de proveedores
- Métricas de rendimiento
- Base de datos (modelos Django + ChromaDB + metadata de review)

**Cuándo leerlo:**
- Quieres entender cómo funciona el sistema internamente
- Estás desarrollando nuevas features
- Necesitas optimizar rendimiento
- Debugging de problemas técnicos
- Planificación de escalabilidad

**Diagramas que encontrarás:**
- Flujo de ejecución completo (9 pasos)
- Arquitectura de componentes
- Integración entre Django y agent_ia_core

---

### ⚙️ **CONFIGURACION_AGENTE.md**

**Qué contiene:**
- Configuración completa del agente RAG
- Variables de entorno (.env)
- Configuración por proveedor
- Parámetros de retrieval
- Opciones de grading y verificación
- Configuración de ChromaDB
- Límites y timeouts

**Cuándo leerlo:**
- Configuración inicial del sistema
- Ajustar parámetros de rendimiento
- Cambiar proveedor LLM
- Optimizar retrieval
- Debugging de problemas de configuración

**Variables importantes:**
```env
USE_FUNCTION_CALLING=true
LLM_PROVIDER=ollama
DEFAULT_K_RETRIEVE=6
LLM_TEMPERATURE=0.3
```

---

### 🔄 **FLUJO_EJECUCION_CHAT.md**

**Qué contiene:**
- Flujo completo de una consulta de chat v3.7
- **9 pasos detallados** desde frontend hasta respuesta:
  1. Usuario envía mensaje
  2. Django Views prepara historial
  3. ChatAgentService - Iteración 1
  4. FunctionCallingAgent ejecuta tools
  5. **ResponseReviewer - Revisión ⭐ NUEVO** (Formato 30%, Contenido 40%, Análisis 30%)
  6. **Segunda Iteración - Mejora ⭐ SIEMPRE ejecutada**
  7. Merge de resultados (documentos + tools)
  8. Guardar en BD con metadata de review
  9. Respuesta al frontend
- Integración completa con agent_ia_core
- Procesamiento de tool calls con hasta 15 iteraciones
- Decisión de mejora automática (SIEMPRE mejorar)
- 3 ejemplos reales de Review Loop
- Tabla de métricas (tokens, latencia)

**Cuándo leerlo:**
- Debugging de flujo de chat
- Entender cómo se procesan las consultas
- Desarrollo de nuevas features de chat
- Optimización de latencia

---

### 📝 **Historial de Versiones**

**Versiones principales:**
- **v3.7.0** (actual): BrowseInteractiveTool con Playwright - Navegación web interactiva
- **v3.6.0**: Review Loop automático - ResponseReviewer que mejora TODAS las respuestas
- **v3.0.0**: Sistema Function Calling completo con 16 tools
- **v1.4.0**: Routing per-message + Ollama (100% local)
- **v1.3.0**: Descarga TED mejorada con cancelación
- **v1.2.0**: Recomendaciones IA multicriteria
- **v1.1.0**: Descarga TED inicial
- **v1.0.0**: Lanzamiento inicial

**Roadmap v4.0+:**
- Multi-Agent Orchestration
- Tool Learning dinámico
- Streaming de respuestas (SSE/WebSocket)
- Cache de Function Calls
- Dashboard Analytics

**Nota:** CHANGELOG.md eliminado por solicitud del usuario. Ver README.md sección "Notas de Versión".

---

## 🎓 Guías por Rol

### Para Usuarios Finales

**Lee en orden:**
1. README.md (sección "Guía de Uso")
2. TOOLS_REFERENCE.md (ejemplos de uso)

**Preguntas frecuentes:**
- ¿Cómo buscar licitaciones? → README.md sección "Usar Chat"
- ¿Qué puedo preguntar? → TOOLS_REFERENCE.md sección "Ejemplos"
- ¿Cuál proveedor usar? → README.md sección "Comparación de Proveedores"

---

### Para Administradores

**Lee en orden:**
1. README.md (instalación y configuración)
2. CONFIGURACION_AGENTE.md (configuración avanzada)
3. ARCHITECTURE.md (arquitectura y escalabilidad)

**Preguntas frecuentes:**
- ¿Cómo instalar? → README.md sección "Instalación"
- ¿Cómo configurar Ollama? → README.md sección "Opción A: Ollama"
- ¿Cómo optimizar? → ARCHITECTURE.md sección "Métricas de Rendimiento"

---

### Para Desarrolladores

**Lee en orden:**
1. ARCHITECTURE.md (arquitectura completa)
2. TOOLS_REFERENCE.md (referencia de tools)
3. FLUJO_EJECUCION_CHAT.md (flujo de ejecución)
4. Código fuente en `agent_ia_core/`

**Preguntas frecuentes:**
- ¿Cómo funciona Function Calling? → ARCHITECTURE.md sección "FunctionCallingAgent"
- ¿Cómo crear nueva tool? → TOOLS_REFERENCE.md sección "Buenas Prácticas"
- ¿Cómo se ejecuta una query? → FLUJO_EJECUCION_CHAT.md
- ¿Cómo agregar proveedor? → ARCHITECTURE.md sección "Proveedores LLM"

---

## 🔍 Búsqueda Rápida

### ¿Necesitas información sobre...?

**Instalación:**
→ README.md sección "Instalación"

**Proveedores LLM (Ollama, OpenAI, Gemini):**
→ README.md sección "Configuración de Proveedores"
→ ARCHITECTURE.md sección "Proveedores LLM"

**Tools disponibles:**
→ TOOLS_REFERENCE.md (completo)

**Ejemplos de uso:**
→ TOOLS_REFERENCE.md sección "Ejemplos de Uso"

**Arquitectura técnica:**
→ ARCHITECTURE.md

**Configuración avanzada:**
→ CONFIGURACION_AGENTE.md

**Flujo de ejecución:**
→ FLUJO_EJECUCION_CHAT.md

**Historial de cambios:**
→ CHANGELOG.md

**Solución de problemas:**
→ README.md sección "Solución de Problemas"

---

## 📊 Comparación de Documentos

| Documento | Audiencia | Complejidad | Tiempo Lectura | Versión |
|-----------|-----------|-------------|----------------|---------|
| README.md | Todos | Baja | 15-20 min | v3.7.0 |
| TOOLS_REFERENCE.md | Usuarios + Devs | Media | 25-35 min | v3.7.0 |
| ARCHITECTURE.md | Devs + Admins | Alta | 35-50 min | v3.7.0 |
| FLUJO_EJECUCION_CHAT.md | Devs | Media-Alta | 20-25 min | v3.7.0 |
| CONFIGURACION_AGENTE.md | Admins + Devs | Media | 15-20 min | v3.0.0 |
| GUIA_INSTALACION_OLLAMA.md | Admins | Baja | 10-15 min | v1.4.0 |

**Notas:**
- ✅ 6 documentos esenciales actualizados (eliminados 9 archivos obsoletos)
- ⭐ Nuevos en v3.7: BrowseInteractiveTool, Review Loop detallado
- 📖 Todos los docs actualizados con 16 tools (vs 9 en v3.0)

---

## 🎯 Casos de Uso

### Caso 1: "Soy nuevo, ¿por dónde empiezo?"

1. **README.md** - Entender qué hace el sistema
2. **README.md** (instalación) - Instalar el sistema
3. **TOOLS_REFERENCE.md** - Ver ejemplos de consultas
4. **Probar en el chat** - Hacer preguntas

---

### Caso 2: "Quiero agregar una nueva tool"

1. **ARCHITECTURE.md** - Entender arquitectura de tools
2. **TOOLS_REFERENCE.md** - Ver estructura de tools existentes
3. **Código fuente** `agent_ia_core/tools/base.py` - Ver clase base
4. **Código fuente** `agent_ia_core/tools/search_tools.py` - Ver ejemplos
5. Implementar nueva tool
6. Registrar en `registry.py`

---

### Caso 3: "El chat no funciona bien"

1. **README.md** (Solución de Problemas) - Problemas comunes
2. **CONFIGURACION_AGENTE.md** - Verificar configuración
3. **FLUJO_EJECUCION_CHAT.md** - Entender flujo para debugging
4. **Logs del servidor** - Ver errores específicos

---

### Caso 4: "Quiero cambiar de Ollama a OpenAI"

1. **README.md** (Opción B: OpenAI) - Instrucciones específicas
2. **CONFIGURACION_AGENTE.md** - Verificar variables de entorno
3. **Perfil de usuario** - Cambiar proveedor y API key
4. **ARCHITECTURE.md** (Proveedores) - Entender diferencias

---

## 📁 Estructura de Archivos

```
TenderAI_Platform/
├── DOCS_INDEX.md                      ← Este archivo (índice de docs) ✅ v3.7
├── README.md                          ← Documentación principal ✅ v3.7
├── TOOLS_REFERENCE.md                 ← Referencia de las 16 tools ✅ v3.7
├── ARCHITECTURE.md                    ← Arquitectura técnica ✅ v3.7
├── FLUJO_EJECUCION_CHAT.md            ← Flujo con Review Loop ✅ v3.7
├── CONFIGURACION_AGENTE.md            ← Configuración del agente
├── GUIA_INSTALACION_OLLAMA.md         ← Instalación de Ollama
└── agent_ia_core/                     ← Código fuente
    ├── agent_function_calling.py      ← FunctionCallingAgent (max 15 iter)
    ├── retriever.py                   ← ChromaDB + embeddings
    └── tools/
        ├── base.py                    ← Clase base de tools
        ├── context_tools.py           ← get_company_info, get_tenders_summary
        ├── search_tools.py            ← 5 tools de búsqueda
        ├── tender_tools.py            ← get_tender_details, get_tender_xml
        ├── analysis_tools.py          ← get_statistics, compare_tenders
        ├── quality_tools.py           ← grade_documents, verify_fields
        ├── web_search_tool.py         ← web_search (Google Custom Search)
        ├── browse_webpage_tool.py     ← browse_webpage (HTML estático)
        ├── browse_interactive_tool.py ← browse_interactive (Playwright) ⭐ v3.7
        ├── registry.py                ← ToolRegistry (16 tools)
        └── schema_converters.py       ← SchemaConverter multi-proveedor

chat/
    ├── response_reviewer.py           ← ResponseReviewer ⭐ v3.6
    └── services.py                    ← ChatAgentService (Review Loop)
```

**Archivos eliminados (obsoletos):**
- ❌ AJAX_RENDERING_FIX.md
- ❌ CONTEXT_TOOLS_FIXES.md
- ❌ CONTEXT_TOOLS_IMPLEMENTATION.md
- ❌ EMBEDDINGS_FIX.md
- ❌ INSTRUCCIONES_DEBUG_LOGIN.md
- ❌ MARKDOWN_FORMAT_IMPROVEMENTS.md
- ❌ REINDEXACION_CONTACTOS.md
- ❌ SISTEMA_LOGGING.md
- ❌ TENDER_ID_SEARCH_FIX.md

---

## 🔗 Enlaces Rápidos

- **Inicio**: [README.md](README.md) ✅ v3.7
- **Tools (16)**: [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) ✅ v3.7
- **Arquitectura**: [ARCHITECTURE.md](ARCHITECTURE.md) ✅ v3.7
- **Flujo + Review Loop**: [FLUJO_EJECUCION_CHAT.md](FLUJO_EJECUCION_CHAT.md) ✅ v3.7
- **Configuración**: [CONFIGURACION_AGENTE.md](CONFIGURACION_AGENTE.md)
- **Ollama**: [GUIA_INSTALACION_OLLAMA.md](GUIA_INSTALACION_OLLAMA.md)

---

## 💡 Consejos

- **Primero README**: Siempre empieza por [README.md](README.md)
- **16 Tools**: [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) tiene ejemplos detallados de todas las tools
- **Review Loop**: [FLUJO_EJECUCION_CHAT.md](FLUJO_EJECUCION_CHAT.md) explica cómo funciona la mejora automática
- **Arquitectura para debugging**: [ARCHITECTURE.md](ARCHITECTURE.md) es clave para resolver problemas técnicos
- **Usa Ctrl+F**: Busca palabras clave en cada documento (ej: "browse_interactive", "review_loop")
- **Docs actualizados**: Toda la documentación está en v3.7.0 (eliminados archivos obsoletos)

---

## 📌 Resumen de Cambios v3.7

**Documentación actualizada:**
- ✅ README.md - Características principales, instalación Playwright, ejemplos de uso
- ✅ ARCHITECTURE.md - ResponseReviewer, BrowseInteractiveTool, Review Loop
- ✅ TOOLS_REFERENCE.md - 16 tools (11 activas + 5 opcionales)
- ✅ FLUJO_EJECUCION_CHAT.md - 9 pasos con Review Loop automático
- ✅ DOCS_INDEX.md - Índice actualizado con nuevas features

**Archivos eliminados:**
- ❌ 9 archivos MD obsoletos (fixes ya integrados)

**Nuevas features documentadas:**
- ⭐ BrowseInteractiveTool con Playwright (navegación web interactiva)
- ⭐ Review Loop automático (ResponseReviewer + 2 iteraciones SIEMPRE)
- ⭐ 16 tools totales (vs 9 en v3.0)
- ⭐ Hasta 15 iteraciones automáticas del agente

---

**🤖 Documentación actualizada a v3.7.0**

**Co-Authored-By: Claude <noreply@anthropic.com>**
