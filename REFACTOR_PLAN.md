# Plan de Refactorización: Sistema de Tools Modular

## Estado: COMPLETADO ✅ (100%)

## Objetivo
Reestructurar el sistema de tools para que sea:
- **Autodescubrible**: Cada archivo = 1 tool automáticamente disponible
- **Modular**: Una sola fuente de verdad para descripciones
- **Claro**: Estructura plana, fácil de entender y mantener

## Progreso

### ✅ COMPLETADO (100%)

1. **Nueva clase base `ToolDefinition`** ([base.py](agent_ia_core/tools/base.py))
   - ✅ Reemplaza `BaseTool` (clase abstracta) con dataclass simple
   - ✅ Métodos: `to_openai_format()`, `to_gemini_format()`, `get_reviewer_format()`
   - ✅ Una sola fuente de verdad para name, description, parameters

2. **Carpeta auxiliary/** - Funciones compartidas NO-tools
   - ✅ `search_base.py`: semantic_search_single(), semantic_search_multiple()
   - ✅ `formatting.py`: format_tender_summary(), format_search_results()

3. **Autodiscovery en `__init__.py`**
   - ✅ Escanear todos los `.py` en tools/
   - ✅ Importar `TOOL_DEFINITION` de cada uno
   - ✅ Exportar `ALL_TOOLS` list
   - ✅ Logs informativos durante el proceso

4. **Tools migradas a nueva estructura (14/14)** ✅ COMPLETADO
   - ✅ `find_best_tender.py` - LA mejor licitación (singular)
   - ✅ `find_top_tenders.py` - X mejores licitaciones (plural)
   - ✅ `get_tender_details.py` - Detalles completos de una licitación
   - ✅ `get_tender_xml.py` - XML completo de licitación
   - ✅ `compare_tenders.py` - Comparar múltiples licitaciones
   - ✅ `get_statistics.py` - Estadísticas de licitaciones
   - ✅ `find_by_budget.py` - Buscar por rango de presupuesto
   - ✅ `find_by_deadline.py` - Buscar por fecha límite
   - ✅ `find_by_cpv.py` - Buscar por código CPV
   - ✅ `find_by_location.py` - Buscar por ubicación
   - ✅ `get_company_info.py` - Info de empresa del usuario
   - ✅ `get_tenders_summary.py` - Resumen de licitaciones guardadas
   - ✅ `web_search.py` - **NUEVO:** Búsqueda web con Google Custom Search API
   - ✅ `browse_webpage.py` - **NUEVO:** Extracción progresiva de información de URLs

5. **Actualizar registry.py** ✅ COMPLETADO
   - ✅ Eliminar imports manuales de tools antiguos
   - ✅ Usar `from agent_ia_core.tools import ALL_TOOLS`
   - ✅ Método `get_reviewer_tools_description()` dinámico
   - ✅ Inyección automática de dependencias (retriever, db_session, user)
   - ✅ **NUEVO:** Inyección de LLM para browse_webpage
   - ✅ **NUEVO:** Inyección de google_api_key y google_engine_id para web_search

6. **Actualizar `response_reviewer.py`** ✅ COMPLETADO
   - ✅ Agregar `tool_registry` al `__init__`
   - ✅ Usar `tool_registry.get_reviewer_tools_description()` en prompt
   - ✅ Fallback con lista estática para backward compatibility
   - ✅ Se mantiene en `apps/chat/` (no se movió a `agent_ia_core/`)

7. **Actualizar `apps/chat/services.py`** ✅ COMPLETADO
   - ✅ Pasar `tool_registry` al crear ResponseReviewer
   - ✅ reviewer = ResponseReviewer(llm, tool_registry=agent.tool_registry, chat_logger=logger)

### 📋 OPCIONAL (No realizado)

8. **Fix logging en `logging_config.py`** ⏸️ NO PRIORITARIO
   - El logging actual funciona correctamente
   - Mejora potencial para versiones futuras

## Estructura Final

```
agent_ia_core/
├── tools/
│   ├── __init__.py              # Autodiscovery: ALL_TOOLS
│   ├── base.py                  # ✅ ToolDefinition
│   │
│   ├── auxiliary/               # 🔄 Funciones compartidas
│   │   ├── __init__.py
│   │   ├── search_base.py
│   │   ├── formatting.py
│   │   └── validation.py
│   │
│   ├── find_best_tender.py      # Tool 1
│   ├── find_top_tenders.py      # Tool 2
│   ├── get_tender_details.py    # Tool 3
│   └── ...                      # Más tools
│
├── registry.py                  # ToolRegistry con autodiscovery
└── response_reviewer.py         # Movido desde apps/chat/
```

## Beneficios

✅ **Autodescubrible** - Agregar tool = crear 1 archivo
✅ **Una fuente de verdad** - description se usa en LLM, reviewer, logs
✅ **Estructura plana** - Fácil encontrar cada tool
✅ **Funciones auxiliares** - Código compartido en auxiliary/
✅ **Logging correcto** - Nombres de tools se extraen bien

## Próximos Pasos

1. Terminar carpeta auxiliary/ con funciones base
2. Migrar una tool como ejemplo (find_best_tender.py)
3. Implementar autodiscovery
4. Migrar todas las demás tools
5. Actualizar registry y response_reviewer
6. Fix logging
7. Testing completo

---

**Fecha**: 2025-12-02
**Responsable**: Claude Code
**Estado**: 100% completado ✅

## Resumen de Cambios

**Archivos creados:**
- [agent_ia_core/tools/base.py](agent_ia_core/tools/base.py) - ToolDefinition dataclass
- [agent_ia_core/tools/__init__.py](agent_ia_core/tools/__init__.py) - Sistema de autodiscovery
- [agent_ia_core/tools/auxiliary/](agent_ia_core/tools/auxiliary/) - Funciones auxiliares compartidas
- 12 archivos de tools individuales (find_best_tender.py, find_top_tenders.py, etc.)

**Archivos modificados:**
- [agent_ia_core/tools/registry.py](agent_ia_core/tools/registry.py) - Autodiscovery + inyección de dependencias
- [apps/chat/response_reviewer.py](apps/chat/response_reviewer.py) - Descripciones dinámicas de tools
- [apps/chat/services.py](apps/chat/services.py) - Pasar tool_registry al reviewer

**Commits realizados:**
1. `refactor: Sistema modular de tools con autodiscovery (Fase 1/3)` - Base y auxiliary
2. `refactor: Migración completa de 12 tools a nueva estructura modular (Fase 2/3)` - Todas las tools
3. `refactor: Actualizar registry.py para usar autodiscovery con ToolDefinition` - Registry
4. `refactor: Response reviewer con descripciones dinámicas de tools` - Reviewer integration
5. `feat: Nuevas web tools (web_search + browse_webpage) con workflow de 2 pasos` - Web tools integration

---

## 🌐 Nuevas Web Tools (Fecha: 2025-12-02)

### Workflow de 2 Pasos

Se han agregado 2 nuevas tools que funcionan en conjunto siguiendo un **workflow de exploración → profundización**:

#### 1️⃣ `web_search.py` - Exploración Amplia
- **Propósito**: Buscar información en internet y encontrar URLs relevantes
- **API**: Google Custom Search API
- **Output**: Lista de resultados con títulos, snippets (150-200 chars), URLs
- **Cuándo usar**: Información NO disponible en BD de licitaciones, precios actuales, noticias, empresas, specs técnicas, regulaciones
- **Parámetros requeridos**: `query` (string), `limit` (int, 1-10, default 5)
- **Dependencias inyectadas**: `api_key`, `engine_id` (desde user config)

#### 2️⃣ `browse_webpage.py` - Profundización Precisa
- **Propósito**: Extraer información ESPECÍFICA de una URL usando las URLs encontradas por web_search
- **Tecnología**: BeautifulSoup + Requests + **Extracción Progresiva con LLM**
- **Característica Especial**: Early stopping - procesa chunks hasta encontrar respuesta
- **Output**: Respuesta extraída (no todo el contenido)
- **Cuándo usar**: DESPUÉS de web_search, para datos exactos/detallados
- **Parámetros requeridos**: `url` (string), `user_query` (string)
- **Parámetros opcionales**: `max_chars` (int, default 10000), `chunk_size` (int, default 1250)
- **Dependencias inyectadas**: `llm` (ChatOpenAI/ChatGemini instance)

### Extracción Progresiva (browse_webpage)

**Algoritmo inteligente con early stopping:**

1. Descarga y limpia HTML de la URL
2. Divide contenido en chunks de N caracteres (configurable)
3. Para cada chunk secuencialmente:
   - Envía al LLM: "¿Este fragmento responde la pregunta X?"
   - Si LLM responde "NO" → continúa con siguiente chunk
   - Si LLM responde con contenido → **DETIENE** extracción (early stopping)
4. Retorna respuesta encontrada + métricas (chars analizados, chars ahorrados, eficiencia %)

**Beneficios:**
- ✅ Ahorra tokens (no procesa contenido innecesario)
- ✅ Más rápido (detiene apenas encuentra respuesta)
- ✅ Contexto conversacional (LLM recuerda fragmentos anteriores)
- ✅ Respuestas directas (sin frases como "Según el fragmento...")

### Ejemplo de Uso Completo

```
Usuario: "¿Cuál es el precio EXACTO del Bitcoin?"

→ PASO 1: web_search
   query: "precio Bitcoin coinbase actual"
   → Resultado: [
       {title: "Bitcoin Price - Coinbase", url: "https://coinbase.com/prices/bitcoin", snippet: "Buy and sell Bitcoin..."},
       ...
     ]

→ PASO 2: browse_webpage
   url: "https://coinbase.com/prices/bitcoin"
   user_query: "precio exacto Bitcoin USD"
   → Chunk 1: "Bitcoin (BTC) ... comprar..." → LLM: "NO"
   → Chunk 2: "Precio actual: $65,432.50 USD" → LLM: "$65,432.50 USD" ✓
   → Early stopping! (ahorro: 80% de contenido no procesado)

→ RESPUESTA FINAL al usuario:
   "El precio actual de Bitcoin es $65,432.50 USD según Coinbase."
```

### Configuración Requerida

**En user model (Django):**
```python
user.use_web_search = True  # Habilitar web tools
user.google_search_api_key = "AIzaSy..."  # Google Custom Search API Key
user.google_search_engine_id = "a1b2c3d..."  # Search Engine ID (cx parameter)
```

**En registry initialization:**
```python
registry = ToolRegistry(
    retriever=retriever,
    user=user,
    llm=llm,  # Para browse_webpage
    google_api_key=user.google_search_api_key,
    google_engine_id=user.google_search_engine_id
)
```

### Mensajes en Logs

```
[REGISTRY] ✓ Web tools (web_search + browse_webpage) habilitadas con credenciales Google
[WEB_SEARCH] Buscando: 'precio Bitcoin' (limit=5)
[WEB_SEARCH] ✓ Encontrados 5 resultados
[BROWSE] Navegando a: https://coinbase.com/prices/bitcoin
[BROWSE] Contenido extraído: 15234 caracteres
[BROWSE] Iniciando extracción progresiva con user_query: 'precio exacto Bitcoin USD'
[BROWSE] Procesando chunk 1 (1250 chars)
[BROWSE] Procesando chunk 2 (1250 chars)
[BROWSE] ✓ Respuesta encontrada en chunk 2/12. Ahorro: 12734 chars (83.6%)
```
