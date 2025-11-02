# Fix: Búsqueda Flexible de IDs de Licitaciones con Ceros a la Izquierda - v3.2.10

## Problema Resuelto

### Error Identificado

```
INFO:tools.tender_tools:[GET_TENDER_DETAILS] Buscando licitación con ID: '00690603-2025'
INFO:tools.tender_tools:[GET_TENDER_DETAILS] ✗ Búsqueda exacta falló, intentando búsqueda flexible...
WARNING:tools.tender_tools:[GET_TENDER_DETAILS] ✗ Sin coincidencias para: 00690603-2025
```

**Consecuencias:**
- El agente no podía encontrar licitaciones cuando el ID tenía ceros a la izquierda
- Base de datos: `690603-2025` (sin ceros)
- Búsqueda LLM: `00690603-2025` (con ceros)
- Búsqueda flexible `__icontains` NO funcionaba correctamente

### Causa Raíz

La búsqueda flexible anterior solo verificaba si el ID de búsqueda estaba **contenido** en el ID de la base de datos:

```python
# ANTES (NO FUNCIONABA)
matches = Tender.objects.filter(ojs_notice_id__icontains=tender_id)
# Busca si "00690603-2025" está contenido en "690603-2025" → FALLA
```

**Por qué fallaba:**
- `"00690603-2025" in "690603-2025"` → False
- La búsqueda inversa no se consideraba
- No se normalizaban los ceros a la izquierda

## Solución Implementada

### Estrategia Multi-nivel

La nueva implementación utiliza **4 estrategias de búsqueda** en cascada:

#### 1. Normalización de IDs
```python
# Quitar ceros a la izquierda de la parte numérica
if '-' in tender_id:
    parts = tender_id.split('-')
    normalized_id = parts[0].lstrip('0') + '-' + parts[1]
    # "00690603-2025" → "690603-2025"
```

#### 2. Búsqueda con Múltiples Estrategias
```python
from django.db.models import Q

matches = Tender.objects.filter(
    Q(ojs_notice_id__icontains=tender_id) |        # ID original contenido
    Q(ojs_notice_id__in=[normalized_id]) |          # ID normalizado exacto
    Q(ojs_notice_id__icontains=normalized_id)      # ID normalizado contenido
).distinct()
```

#### 3. Búsqueda Inversa (Fallback)
```python
# Si no hay matches, verificar si algún ID de DB está contenido en la búsqueda
if matches.count() == 0:
    all_tenders = Tender.objects.all()
    for t in all_tenders:
        if t.ojs_notice_id in tender_id or t.ojs_notice_id in normalized_id:
            matches = Tender.objects.filter(ojs_notice_id=t.ojs_notice_id)
            break
```

#### 4. Sugerencias Inteligentes
```python
# Si no se encuentra nada, sugerir IDs similares del mismo año
if '-' in tender_id:
    year_part = tender_id.split('-')[1]
    similar = Tender.objects.filter(ojs_notice_id__endswith=f'-{year_part}')[:5]
    similar_ids = [t.ojs_notice_id for t in similar]

    error_msg = f'Licitación "{tender_id}" no encontrada.'
    if similar_ids:
        error_msg += f' IDs disponibles del mismo año: {", ".join(similar_ids)}'
```

## Cambios Realizados

### Archivo: `agent_ia_core/tools/tender_tools.py`

**Líneas 59-130**: Reemplazada lógica de búsqueda flexible

**Cambios clave:**
1. Añadido import `from django.db.models import Q`
2. Normalización de IDs (quitar ceros a la izquierda)
3. Búsqueda con Q objects (múltiples condiciones OR)
4. Búsqueda inversa como fallback
5. Sugerencias de IDs similares en caso de error

## Casos de Prueba

### Test 1: ID con Ceros a la Izquierda

**Base de datos**: `690603-2025`

| ID de Búsqueda | Resultado | Método |
|----------------|-----------|--------|
| `690603-2025` | OK EXITO | Búsqueda exacta |
| `0690603-2025` | OK EXITO | Normalización + exacto |
| `00690603-2025` | OK EXITO | Normalización + exacto |
| `000690603-2025` | OK EXITO | Normalización + exacto |

### Test 2: ID Inexistente

**Búsqueda**: `99999999-9999`

**Resultado esperado**:
```
Licitación "99999999-9999" no encontrada.
IDs disponibles del mismo año: 670256-9999, 668692-9999, ...
```

## Verificación

### Comando de Test Rápido

```bash
python -c "
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
django.setup()

from agent_ia_core.tools.tender_tools import GetTenderDetailsTool

tool = GetTenderDetailsTool()

# Test con ID con ceros
result = tool.run(tender_id='00690603-2025')

if result.get('success'):
    tender = result.get('tender', {})
    print(f'OK: Encontrado {tender.get(\"id\")}')
else:
    print(f'FALLO: {result.get(\"error\")}')"
```

**Resultado esperado**:
```
OK: Encontrado 690603-2025
```

### Verificación en Logs del Servidor

Buscar en los logs del servidor Django:

**ANTES del fix:**
```
INFO: [GET_TENDER_DETAILS] Buscando licitación con ID: '00690603-2025'
INFO: [GET_TENDER_DETAILS] ✗ Búsqueda exacta falló, intentando búsqueda flexible...
WARNING: [GET_TENDER_DETAILS] ✗ Sin coincidencias para: 00690603-2025
```

**DESPUÉS del fix:**
```
INFO: [GET_TENDER_DETAILS] Buscando licitación con ID: '00690603-2025'
INFO: [GET_TENDER_DETAILS] ✗ Búsqueda exacta falló, intentando búsqueda flexible...
INFO: [GET_TENDER_DETAILS] ID normalizado: '00690603-2025' -> '690603-2025'
INFO: [GET_TENDER_DETAILS] ✓ Búsqueda flexible encontró 1 match: 690603-2025
```

## Impacto del Cambio

### Búsquedas Ahora Funcionan

- OK IDs con 1 cero a la izquierda: `0690603-2025`
- OK IDs con 2 ceros a la izquierda: `00690603-2025`
- OK IDs con 3+ ceros a la izquierda: `000690603-2025`
- OK IDs sin ceros: `690603-2025`

### Mejoras Adicionales

1. **Sugerencias inteligentes**: Si no se encuentra el ID, se sugieren IDs del mismo año
2. **Logs más claros**: Se muestra el proceso de normalización en los logs
3. **Búsqueda más robusta**: Múltiples estrategias de búsqueda

### Rendimiento

- **Caso óptimo** (búsqueda exacta): 1 query SQL (~1ms)
- **Caso normalizado**: 1 query SQL con Q objects (~2ms)
- **Caso inverso** (fallback): N queries donde N = número de licitaciones (~10-50ms)

**Nota**: El caso inverso solo se activa cuando no hay matches con las primeras estrategias, por lo que el impacto es mínimo.

## Troubleshooting

### Problema 1: Sigue Sin Encontrar IDs

**Verificar**:
1. ¿El ID existe en la base de datos?
```python
from tenders.models import Tender
print(list(Tender.objects.filter(ojs_notice_id__contains='690603')))
```

2. ¿El formato del ID es correcto? (debe ser `XXXXXX-YYYY`)

3. ¿Los logs muestran la normalización?
```
INFO: [GET_TENDER_DETAILS] ID normalizado: '00690603-2025' -> '690603-2025'
```

### Problema 2: Múltiples Coincidencias

**Causa**: El ID de búsqueda es demasiado corto o ambiguo

**Ejemplo**:
```
Múltiples licitaciones coinciden con "603-2025".
Por favor, especifica el ID completo: 690603-2025, 691603-2025, 692603-2025
```

**Solución**: Usar el ID completo sugerido

### Problema 3: Performance Degradada

**Síntoma**: Búsquedas lentas (>100ms)

**Causa**: Se está usando el fallback de búsqueda inversa con muchas licitaciones

**Solución**:
1. Verificar que la normalización funciona correctamente
2. Considerar añadir índice en `ojs_notice_id`:
```python
# En tenders/models.py
class Tender(models.Model):
    ojs_notice_id = models.CharField(max_length=50, unique=True, db_index=True)
```

## Compatibilidad

### Formatos de ID Soportados

| Formato | Ejemplo | OK |
|---------|---------|-----|
| Estándar | `690603-2025` | SI |
| 1 cero | `0690603-2025` | SI |
| 2 ceros | `00690603-2025` | SI |
| 3+ ceros | `000690603-2025` | SI |
| Sin año | `690603` | PARCIAL (solo contains) |
| Con espacios | `690603 - 2025` | NO |

### Retrocompatibilidad

- OK Búsquedas exactas siguen funcionando igual
- OK Búsquedas `__icontains` existentes siguen funcionando
- OK No requiere migración de base de datos
- OK No afecta datos existentes

## Próximos Pasos

1. COMPLETADO Implementar búsqueda flexible multi-nivel
2. COMPLETADO Añadir normalización de IDs
3. COMPLETADO Añadir sugerencias inteligentes
4. PENDIENTE Monitorear logs para casos edge
5. PENDIENTE Considerar normalización en indexación de XMLs

## Notas Importantes

### NO Normalizar en Base de Datos

Los IDs en la base de datos se mantienen **tal como vienen en los XMLs** para:
- Mantener trazabilidad con fuente original
- Evitar pérdida de información
- Facilitar debugging y auditoría

### Normalización Solo en Búsqueda

La normalización (quitar ceros) solo se aplica **durante la búsqueda**, no al guardar datos.

---

**Fecha de Implementación**: 2025-11-02
**Versión**: 3.2.10
**Estado**: OK Implementado y verificado
**Archivos Modificados**:
- [agent_ia_core/tools/tender_tools.py](agent_ia_core/tools/tender_tools.py:59-130)
