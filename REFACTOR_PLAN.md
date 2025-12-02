# Plan de Refactorización: Sistema de Tools Modular

## Estado: FASE 2 COMPLETADA (90%)

## Objetivo
Reestructurar el sistema de tools para que sea:
- **Autodescubrible**: Cada archivo = 1 tool automáticamente disponible
- **Modular**: Una sola fuente de verdad para descripciones
- **Claro**: Estructura plana, fácil de entender y mantener

## Progreso

### ✅ COMPLETADO (90%)

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

4. **Tools migradas a nueva estructura (12/12)** ✅ COMPLETADO
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

### 📋 PENDIENTE (10%)

5. **Actualizar registry.py** ⏳ EN PROGRESO
   - ⏳ Eliminar imports manuales de tools antiguos
   - ⏳ Usar `from agent_ia_core.tools import ALL_TOOLS`
   - ⏳ Método `get_reviewer_tools_description()` dinámico
   - ⏳ Adaptador para compatibilidad con código existente

6. **Mover y actualizar `response_reviewer.py`** ⏳ PENDIENTE
   - ⏳ Mover de `apps/chat/` a `agent_ia_core/`
   - ⏳ Agregar `tool_registry` al `__init__`
   - ⏳ Usar `tool_registry.get_reviewer_tools_description()` en prompt

7. **Actualizar `apps/chat/services.py`** ⏳ PENDIENTE
   - ⏳ Cambiar import: `from agent_ia_core.response_reviewer import ResponseReviewer`
   - ⏳ Pasar `tool_registry` al crear ResponseReviewer

8. **Fix logging en `logging_config.py`** ⏳ PENDIENTE
   - ⏳ Extraer nombre correctamente de formato OpenAI: `tool['function']['name']`
   - ⏳ Extraer nombre correctamente de formato Gemini: `tool['name']`

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
**Estado**: 90% completado (12/12 tools migradas)
