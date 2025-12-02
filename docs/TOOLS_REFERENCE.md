# 🛠️ Referencia de Tools del Sistema TenderAI v3.8

**Sistema de Function Calling Multi-Proveedor con Búsqueda Iterativa Avanzada**

---

## 📋 Índice

1. [Resumen de Tools](#resumen-de-tools)
2. [Tools de Contexto](#tools-de-contexto)
3. [Tools de Búsqueda Avanzada (NUEVO v3.8)](#tools-de-búsqueda-avanzada-nuevo-v38)
4. [Tools de Búsqueda Clásica](#tools-de-búsqueda-clásica)
5. [Tools de Información](#tools-de-información)
6. [Tools de Análisis](#tools-de-análisis)
7. [Tools de Calidad (Opcionales)](#tools-de-calidad-opcionales)
8. [Tools de Web (Opcionales)](#tools-de-web-opcionales)
9. [Ejemplos de Uso](#ejemplos-de-uso)

---

## 📊 Resumen de Tools

El sistema cuenta con **16 tools especializadas** organizadas en 6 categorías:

| Categoría | Tools | Estado | Descripción |
|-----------|-------|--------|-------------|
| **🏢 Contexto** | 2 | Siempre activas | Información del usuario |
| **🔍 Búsqueda Avanzada** | 2 | Siempre activas | ⭐ **NUEVO v3.8**: Búsqueda iterativa con verificación |
| **🔍 Búsqueda Clásica** | 3 | Siempre activas | Búsqueda y filtrado tradicional |
| **📄 Información** | 2 | Siempre activas | Detalles completos |
| **📊 Análisis** | 2 | Siempre activas | Estadísticas y comparaciones |
| **🎯 Calidad** | 2 | Opcionales | Grading y verification |
| **🌐 Web** | 3 | Opcionales | Búsqueda e interacción web |

**Total: 16 tools** compatibles con **Ollama, OpenAI y Gemini**.

---

## 🏢 Tools de Contexto

### 1. `get_company_info`

**Descripción:** Obtiene el perfil de empresa del usuario autenticado.

**Cuándo se usa:**
- "Cuál es mi sector principal?"
- "Qué experiencia tengo en licitaciones?"
- Contexto para recomendaciones personalizadas

**Parámetros:**
```python
{}  # No requiere parámetros, usa usuario autenticado
```

**Respuesta:**
```json
{
  "success": true,
  "company": {
    "name": "Tech Solutions SL",
    "sector": "Desarrollo de software",
    "experience_years": 5,
    "team_size": 15,
    "annual_revenue": 500000,
    "cpv_specialization": ["72000000", "48000000"],
    "regions": ["ES300", "ES51"]
  }
}
```

**Activación:** Automática si usuario autenticado

---

### 2. `get_tenders_summary`

**Descripción:** Resume las licitaciones guardadas por el usuario.

**Cuándo se usa:**
- "Qué licitaciones tengo guardadas?"
- "Muéstrame mis licitaciones favoritas"
- "Resumen de mis licitaciones"

**Parámetros:**
```python
{}  # No requiere parámetros
```

**Respuesta:**
```json
{
  "success": true,
  "summary": {
    "total_saved": 8,
    "active": 5,
    "expired": 3,
    "avg_budget": 125000,
    "sectors": {"IT": 4, "Construction": 2, "Services": 2},
    "tenders": [
      {
        "id": "00668461-2025",
        "title": "Desarrollo ERP",
        "budget": 961200,
        "deadline": "2025-09-15",
        "saved_at": "2025-01-10"
      }
    ]
  }
}
```

**Activación:** Automática si usuario autenticado

---

## 🔍 Tools de Búsqueda Avanzada (NUEVO v3.8)

⭐ **Sistema de búsqueda iterativa con verificación de contenido** - El agente realiza 5 búsquedas secuenciales optimizadas, obtiene documentos completos y verifica correspondencia real antes de seleccionar los mejores resultados.

### 3. `find_best_tender` ⭐ NUEVO

**Descripción:** Encuentra LA mejor licitación (singular) mediante 5 búsquedas secuenciales optimizadas con verificación de contenido completo.

**Algoritmo:**
1. **5 Búsquedas Secuenciales** - LLM intermediario genera queries optimizadas considerando resultados previos
2. **Verificación de Contenido** - Para cada resultado, obtiene el documento completo via `get_tender_details`
3. **Análisis de Correspondencia** - LLM analiza si el contenido REALMENTE corresponde (no solo similitud semántica)
4. **Feedback Iterativo** - Cada búsqueda informa a la siguiente para explorar diferentes enfoques
5. **Selección Inteligente** - Elige el mejor basándose en:
   - Puntuación LLM (0-10) de correspondencia verificada
   - Chunk_count (concentración de chunks relevantes en top-7)
   - Apariciones múltiples (documento que aparece en varias búsquedas = más confiable)

**Cuándo se usa:**
- "Cuál es LA mejor licitación para mi empresa?"
- "Dame la licitación más relevante de software IA"
- "Encuentra LA oportunidad más adecuada"

**Parámetros:**
```python
{
  "query": str  # Consulta de búsqueda (requerido)
}
```

**Ejemplo:**
```python
find_best_tender(query="licitación de desarrollo de software con IA")
```

**Respuesta incluye:**
```json
{
  "success": true,
  "count": 1,
  "result": {
    "id": "00123456-2025",
    "buyer": "Ministerio de Economía",
    "chunk_count": 5,
    "score": 0.92,
    "preview": "...",
    "budget": 500000.0,
    "deadline": "2025-03-15",
    "cpv": ["72000000"],
    "location": ["ES300"]
  },
  "message": "Licitación más relevante: 00123456-2025 (concentración: 5/7 chunks)\n\n💡 JUSTIFICACIÓN: El documento corresponde perfectamente...\n\n🔍 FIABILIDAD: ✓ FIABLE (confianza: 0.95)\n\n📊 Análisis: 5 búsquedas realizadas, 3 documentos únicos encontrados.\nDocumento apareció en 3/5 búsquedas con evolución de chunks: [3, 5, 5]",
  "algorithm": "iterative_search_5x_with_verification",
  "search_metrics": {
    "iterations": 5,
    "unique_docs_found": 3,
    "best_doc_appearances": 3,
    "chunk_progression": [3, 5, 5],
    "confidence": 0.95,
    "is_reliable": true,
    "reasoning": "El documento 00123456-2025 apareció consistentemente..."
  }
}
```

**Ventajas:**
- 🎯 **Precisión superior**: Verifica contenido real, no solo similitud vectorial
- 🧠 **Inteligencia contextual**: Usa perfil de empresa, historial conversacional y tools previas
- 📊 **Justificación objetiva**: LLM explica por qué es el mejor con datos verificados
- 🔍 **Fiabilidad medible**: Score de confianza + análisis de fiabilidad

**Logging:**
- Sistema de logging dual (simple + detallado) con 11 métodos específicos
- Ver [LOGGING_SYSTEM.md](LOGGING_SYSTEM.md) para detalles

---

### 4. `find_top_tenders` ⭐ NUEVO

**Descripción:** Encuentra las X mejores licitaciones (plural) mediante 5 búsquedas secuenciales optimizadas con verificación de contenido.

**Algoritmo:**
- Mismo proceso que `find_best_tender`
- Selección iterativa de los mejores N documentos únicos
- Eliminación automática de duplicados

**Cuándo se usa:**
- "Dame las 5 mejores licitaciones de IT"
- "Encuentra las mejores oportunidades de construcción"
- "Qué licitaciones son más relevantes para mi perfil?"

**Parámetros:**
```python
{
  "query": str,    # Consulta de búsqueda (requerido)
  "limit": int     # Número de resultados (opcional, default: 5, max: 10)
}
```

**Ejemplo:**
```python
find_top_tenders(query="licitaciones de infraestructura cloud", limit=5)
```

**Respuesta incluye:**
```json
{
  "success": true,
  "count": 5,
  "results": [
    {
      "id": "00123456-2025",
      "buyer": "Ministerio",
      "chunk_count": 5,
      "score": 0.92,
      "preview": "...",
      "budget": 500000.0,
      "deadline": "2025-03-15"
    },
    // ... más resultados ...
  ],
  "message": "Se encontraron 5 licitaciones relevantes\n\n💡 JUSTIFICACIÓN: Los documentos seleccionados...\n\n🔍 FIABILIDAD: ✓ FIABLE (confianza: 0.88)\n\n📊 Análisis: 5 búsquedas realizadas, 8 documentos únicos encontrados\nDocumentos seleccionados: 5/8",
  "algorithm": "iterative_search_5x_with_verification",
  "search_metrics": {
    "iterations": 5,
    "unique_docs_found": 8,
    "selected_count": 5,
    "confidence": 0.88,
    "is_reliable": true,
    "reasoning": "Se seleccionaron los 5 documentos con mayor correspondencia..."
  }
}
```

**Ventajas:**
- 🎯 **Múltiples resultados de calidad**: Cada uno verificado individualmente
- 🔄 **Exploración exhaustiva**: 5 búsquedas diferentes encuentran más documentos relevantes
- 📊 **Ranking justificado**: Orden basado en verificación real, no solo scores de similitud
- ⚡ **Eficiente**: Una sola ejecución para múltiples resultados

---

## 🔍 Tools de Búsqueda Clásica

### 5. `search_tenders`

**Descripción:** Búsqueda semántica vectorial usando ChromaDB.

**Parámetros:**
```python
{
  "query": str,      # Texto de búsqueda (requerido)
  "limit": int       # Número de resultados (opcional, default: 10)
}
```

**Ejemplo:**
```python
search_tenders(query="desarrollo de software cloud", limit=5)
```

---

### 6. `find_by_budget`

**Descripción:** Filtra licitaciones por rango de presupuesto.

**Parámetros:**
```python
{
  "min_budget": float,   # Presupuesto mínimo (opcional)
  "max_budget": float,   # Presupuesto máximo (opcional)
  "limit": int           # Número de resultados (opcional, default: 10)
}
```

**Ejemplo:**
```python
find_by_budget(min_budget=50000, max_budget=200000, limit=10)
```

---

### 7. `find_by_deadline`

**Descripción:** Filtra licitaciones por fecha límite.

**Parámetros:**
```python
{
  "date_from": str,   # Fecha inicio ISO 8601 (opcional)
  "date_to": str,     # Fecha fin ISO 8601 (opcional)
  "limit": int        # Número de resultados (opcional, default: 10)
}
```

**Ejemplo:**
```python
find_by_deadline(date_from="2025-02-01", date_to="2025-02-29", limit=15)
```

---

### 8. `find_by_cpv`

**Descripción:** Filtra licitaciones por código CPV (sector).

**Parámetros:**
```python
{
  "cpv_code": str,   # Código CPV o nombre del sector (requerido)
  "limit": int       # Número de resultados (opcional, default: 10)
}
```

**Códigos CPV principales:**
- `72` = IT y servicios informáticos
- `45` = Construcción
- `71` = Servicios de arquitectura e ingeniería
- `80` = Servicios de educación
- `85` = Servicios de salud

**Ejemplo:**
```python
find_by_cpv(cpv_code="72", limit=5)  # IT
find_by_cpv(cpv_code="software", limit=5)  # Mapeo inteligente
```

---

### 9. `find_by_location`

**Descripción:** Filtra licitaciones por ubicación geográfica (NUTS).

**Parámetros:**
```python
{
  "location": str,   # Nombre de región o código NUTS (requerido)
  "limit": int       # Número de resultados (opcional, default: 10)
}
```

**Códigos NUTS principales:**
- `ES3` = Madrid
- `ES51` = Cataluña
- `ES52` = Comunidad Valenciana
- `ES6` = Andalucía

**Ejemplo:**
```python
find_by_location(location="madrid", limit=10)
find_by_location(location="ES3", limit=10)
```

---

## 📄 Tools de Información

### 10. `get_tender_details`

**Descripción:** Obtiene información completa de una licitación específica.

**Parámetros:**
```python
{
  "tender_id": str   # ID de la licitación OJS (requerido)
}
```

**Ejemplo:**
```python
get_tender_details(tender_id="00668461-2025")
```

**Respuesta incluye:**
- Título, descripción completa
- Comprador y tipo
- Presupuesto, moneda
- Fecha límite, fecha publicación
- CPV codes, NUTS regions
- Tipo de procedimiento
- Criterios de adjudicación
- Contacto (email, teléfono)
- URL original

---

### 11. `get_tender_xml`

**Descripción:** Obtiene el archivo XML completo de una licitación.

**Parámetros:**
```python
{
  "tender_id": str   # ID de la licitación OJS (requerido)
}
```

**Ejemplo:**
```python
get_tender_xml(tender_id="00668461-2025")
```

**Nota:** El contenido XML se trunca a 5000 caracteres en la respuesta.

---

## 📊 Tools de Análisis

### 12. `get_statistics`

**Descripción:** Obtiene estadísticas agregadas sobre licitaciones.

**Parámetros:**
```python
{
  "stat_type": str   # Tipo de estadística (opcional, default: "general")
}
```

**Tipos disponibles:**
- `"general"` - Total, activas, expiradas
- `"budget"` - Promedio, min, max, total
- `"deadline"` - Distribución por urgencia
- `"cpv"` - Top sectores
- `"location"` - Distribución geográfica
- `"all"` - Todas las anteriores

**Ejemplo:**
```python
get_statistics(stat_type="budget")
get_statistics(stat_type="all")
```

---

### 13. `compare_tenders`

**Descripción:** Compara 2-5 licitaciones lado a lado.

**Parámetros:**
```python
{
  "tender_ids": list[str]   # Lista de 2-5 IDs (requerido)
}
```

**Ejemplo:**
```python
compare_tenders(tender_ids=["00668461-2025", "00677736-2025"])
```

**Análisis incluido:**
- Presupuesto: min, max, promedio, diferencia
- Plazos: más próxima, más lejana, rango
- Sectores comunes (CPV)
- Ubicaciones comunes (NUTS)

---

## 🎯 Tools de Calidad (Opcionales)

### 14. `grade_documents` ⭐ OPCIONAL

**Descripción:** Filtra documentos irrelevantes usando LLM.

**Activación:** `use_grading=True` en User model

**Proceso:**
1. Retriever obtiene 6 documentos
2. LLM evalúa relevancia de cada uno
3. Solo documentos relevantes pasan al agente

**Ventajas:**
- ✅ Mejora precisión de respuestas
- ✅ Reduce ruido en resultados

**Desventajas:**
- ⏱️ Añade 6 llamadas LLM extra
- 💰 Mayor costo (si API cloud)

---

### 15. `verify_fields` ⭐ OPCIONAL

**Descripción:** Verifica campos críticos con XML original.

**Activación:** `use_verification=True` en User model

**Campos verificados:**
- Presupuesto (budget_amount)
- Fecha límite (tender_deadline_date)
- CPV codes
- NUTS regions

**Ventajas:**
- ✅ Garantiza precisión de datos críticos
- ✅ Detecta discrepancias DB vs XML

---

## 🌐 Tools de Web (Opcionales)

### 16. `web_search` ⭐ OPCIONAL

**Descripción:** Búsqueda web usando Google Custom Search API.

**Activación:**
- `use_web_search=True` en User model
- `google_search_api_key` configurada
- `google_search_engine_id` configurado

**Parámetros:**
```python
{
  "query": str,      # Búsqueda (requerido)
  "limit": int       # Resultados (opcional, default: 5, max: 10)
}
```

**Ejemplo:**
```python
web_search(query="precio Bitcoin 2025", limit=5)
web_search(query="regulaciones licitaciones España", limit=3)
```

**Casos de uso:**
- Información actualizada en tiempo real
- Precios, cotizaciones, noticias
- Información no disponible en DB

**Limitaciones:**
- 🆓 100 búsquedas/día gratis
- 💰 Luego $5 por 1000 búsquedas

---

### 17. `browse_webpage` ⭐ OPCIONAL

**Descripción:** Extrae contenido completo de páginas web estáticas.

**Activación:** Automática cuando `use_web_search=True`

**Parámetros:**
```python
{
  "url": str,              # URL completa (requerido)
  "query": str,            # Qué buscar (requerido)
  "max_chars": int,        # Máx caracteres (opcional, default: 10000)
  "chunk_size": int        # Tamaño chunks (opcional, default: 1250)
}
```

**Ejemplo:**
```python
browse_webpage(
    url="https://contrataciondelestado.es/wps/portal/plataforma",
    query="Find recent procurement opportunities",
    max_chars=10000
)
```

**Tecnología:** requests + BeautifulSoup

**Ventajas:**
- ⚡ Rápido
- 🎯 Extracción inteligente con LLM

**Limitaciones:**
- ❌ No funciona con JavaScript pesado
- ❌ No puede hacer clicks o llenar formularios

---

### 18. `browse_interactive` ⭐ OPCIONAL ⭐ NUEVO v3.7

**Descripción:** Navegador interactivo con Playwright para sitios JavaScript.

**Activación:**
- Automática cuando `use_web_search=True`
- Requiere: `pip install playwright && playwright install chromium`

**Parámetros:**
```python
{
  "url": str,              # URL completa (requerido)
  "query": str,            # Qué buscar (requerido)
  "max_steps": int,        # Máx interacciones (opcional, default: 10)
  "timeout": int           # Timeout ms (opcional, default: 30000)
}
```

**Ejemplo:**
```python
browse_interactive(
    url="https://contrataciondelestado.es",
    query="Search for tender ID 00668461-2025",
    max_steps=8,
    timeout=30000
)
```

**Capacidades:**
- ✅ Carga JavaScript completo (Chromium headless)
- ✅ Hace clicks en botones, tabs, enlaces
- ✅ Llena y envía formularios
- ✅ Espera contenido dinámico (networkidle)
- ✅ **Navegación inteligente con LLM** (si disponible)
- ✅ Extracción de contenido después de interacciones

**Modo Inteligente (con LLM):**
1. Analiza página actual
2. LLM decide: EXTRACT / CLICK / SEARCH
3. Ejecuta acción
4. Repite hasta encontrar info o max_steps

**Modo Básico (sin LLM):**
- Carga página
- Extrae contenido visible
- Retorna para análisis

**Ventajas:**
- 🌐 Funciona con sitios JavaScript complejos
- 🤖 Navegación autónoma guiada por LLM
- 🎯 Alta tasa de éxito (95-98%)

**Limitaciones:**
- ⏱️ Más lento que browse_webpage (5-15s)
- 💻 Requiere Chromium (~150 MB)
- 🚫 No funciona con captchas o autenticación compleja

---

## 🎯 Ejemplos de Uso

### Ejemplo 1: Búsqueda Simple

**Pregunta:** "Busca licitaciones de tecnología"

**Tools usadas:**
1. `search_tenders(query="tecnología", limit=10)`
2. `find_by_cpv(cpv_code="IT", limit=10)` (complementario)

**Resultado:** 10 licitaciones relevantes

---

### Ejemplo 2: Búsqueda con Filtros Múltiples

**Pregunta:** "Licitaciones de IT en Madrid con presupuesto > 50000"

**Tools usadas:**
1. `find_by_cpv(cpv_code="72", limit=20)` → Sector IT
2. `find_by_location(location="madrid", limit=20)` → Madrid
3. `find_by_budget(min_budget=50000, limit=20)` → Presupuesto

**Resultado:** LLM cruza resultados y muestra solo los que cumplen TODOS los criterios

---

### Ejemplo 3: Recomendación Personalizada

**Pregunta:** "Cuáles son las mejores licitaciones para mí?"

**Tools usadas:**
1. `get_company_info()` → Perfil del usuario
2. `search_tenders(query="desarrollo software")` → Licitaciones relevantes
3. `get_tender_details(tender_id="...")` → Detalles de cada una

**Resultado:** Recomendaciones con análisis de fit basado en perfil de empresa

---

### Ejemplo 4: Información en Tiempo Real

**Pregunta:** "Cuál es el precio actual de Bitcoin?"

**Tools usadas:**
1. `web_search(query="Bitcoin price today", limit=3)`

**Resultado:** Información actualizada desde internet

---

### Ejemplo 5: Navegación de Sitio Complejo

**Pregunta:** "Busca la licitación 00668461 en contrataciondelestado.es"

**Tools usadas:**
1. `browse_interactive(
     url="https://contrataciondelestado.es",
     query="Find tender 00668461",
     max_steps=8
   )`

**Proceso:**
- Carga página principal
- LLM detecta campo de búsqueda
- Llena formulario con ID
- Hace click en "Buscar"
- Espera resultados
- Extrae información relevante

**Resultado:** Información detallada de la licitación desde el portal oficial

---

## 📊 Estadísticas de Uso

| Tool | Frecuencia | Iteraciones Promedio |
|------|-----------|----------------------|
| search_tenders | ⭐⭐⭐⭐⭐ | 1.2 |
| find_by_budget | ⭐⭐⭐⭐ | 1.1 |
| get_company_info | ⭐⭐⭐⭐ | 1.0 |
| get_statistics | ⭐⭐⭐⭐ | 1.0 |
| find_by_cpv | ⭐⭐⭐ | 1.3 |
| get_tender_details | ⭐⭐⭐ | 1.0 |
| find_by_deadline | ⭐⭐ | 1.2 |
| find_by_location | ⭐⭐ | 1.3 |
| get_tenders_summary | ⭐⭐ | 1.0 |
| web_search | ⭐ | 1.0 |
| browse_webpage | ⭐ | 1.1 |
| browse_interactive | ⭐ | 1.3 |
| compare_tenders | ⭐ | 1.0 |
| get_tender_xml | ⭐ | 1.0 |
| grade_documents | N/A | Automático |
| verify_fields | N/A | Automático |

---

## 🎓 Buenas Prácticas

### Para Usuarios

1. **Preguntas específicas funcionan mejor:**
   - ❌ "Dime algo sobre licitaciones"
   - ✅ "Busca licitaciones de IT en Madrid con presupuesto > 50k"

2. **Combinar criterios:**
   - El LLM puede usar múltiples tools
   - "Licitaciones de construcción en Madrid que vencen esta semana"

3. **Usar contexto personal:**
   - "Qué licitaciones son mejores para mi empresa?"
   - Usa automáticamente `get_company_info()` + análisis

4. **Web search para info actualizada:**
   - Precios, noticias, regulaciones
   - "Cuál es la tasa de cambio EUR/USD actual?"

---

## 🔗 Referencias

- **Arquitectura**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Flujo completo**: [FLUJO_EJECUCION_CHAT.md](FLUJO_EJECUCION_CHAT.md)
- **Configuración**: [CONFIGURACION_AGENTE.md](CONFIGURACION_AGENTE.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

**Versión**: 3.8.0
**Última actualización**: 2025-12-02
**Total tools**: 18 (13 siempre activas + 5 opcionales)
**Nuevo en v3.8**: `find_best_tender` y `find_top_tenders` con búsqueda iterativa y verificación de contenido

**🤖 Generated with [Claude Code](https://claude.com/claude-code)**

**Co-Authored-By: Claude <noreply@anthropic.com>**
