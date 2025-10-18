# Configuración del Agente RAG

Este documento explica todas las configuraciones disponibles para el agente de chat en el archivo `.env`.

## Ubicación

Todas las configuraciones están en el archivo `.env` en la raíz del proyecto, bajo la sección **"CONFIGURACIÓN DEL AGENTE RAG"**.

---

## Historial de Conversación

### `MAX_CONVERSATION_HISTORY`
**Valor por defecto:** `10`
**Descripción:** Número máximo de mensajes previos a incluir como contexto en cada respuesta.

**Valores recomendados:**
- `5` - Contexto mínimo, para sistemas con poca RAM
- `10` - Equilibrio óptimo (recomendado)
- `20` - Contexto extenso, permite referencias más antiguas
- `30+` - Solo para modelos muy grandes con mucha RAM

**Impacto:**
- Mayor valor = Mejor memoria conversacional pero más tokens
- Menor valor = Menos consumo de RAM pero memoria limitada

**Ejemplo de uso:**
```bash
# Para conversaciones más largas con contexto extenso
MAX_CONVERSATION_HISTORY=20
```

---

## Recuperación de Documentos

### `DEFAULT_K_RETRIEVE`
**Valor por defecto:** `6`
**Descripción:** Número de documentos a recuperar del vectorstore para cada consulta.

**Valores recomendados:**
- `3` - Rápido, solo documentos más relevantes
- `6` - Equilibrio óptimo (recomendado)
- `10` - Más contexto, mejor para preguntas complejas
- `15+` - Análisis exhaustivos

**Impacto:**
- Mayor valor = Más contexto pero más tokens y tiempo
- Menor valor = Respuestas más rápidas pero menos completas

### `MIN_SIMILARITY_SCORE`
**Valor por defecto:** `0.5`
**Descripción:** Umbral mínimo de similaridad (0.0-1.0) para considerar un documento relevante.

**Valores recomendados:**
- `0.3` - Permisivo, incluye documentos menos relevantes
- `0.5` - Equilibrio (recomendado)
- `0.7` - Estricto, solo documentos muy relevantes
- `0.9` - Muy estricto, casi coincidencia exacta

**Impacto:**
- Mayor valor = Menos documentos pero más relevantes
- Menor valor = Más documentos pero algunos menos relevantes

---

## LLM Settings

### `LLM_TEMPERATURE`
**Valor por defecto:** `0.3`
**Descripción:** Temperatura para generación de respuestas (0.0-1.0).

**Valores recomendados:**
- `0.0` - Completamente determinista, respuestas idénticas
- `0.3` - Ligeramente creativo (recomendado para chat)
- `0.5` - Balance creatividad/precisión
- `0.7` - Creativo, respuestas variadas
- `1.0` - Muy creativo, impredecible

**Impacto:**
- `0.0` = Ideal para respuestas técnicas precisas
- `0.3` = Ideal para chat profesional natural
- `0.7+` = Ideal para escritura creativa

### `OLLAMA_CONTEXT_LENGTH`
**Valor por defecto:** `2048`
**Descripción:** Longitud de contexto para Ollama en tokens.

**Valores típicos:**
- `1024` - Contexto corto, ~18GB RAM (modelos 72B)
- `2048` - Contexto medio, ~25GB RAM (recomendado)
- `4096` - Contexto largo, ~40GB RAM (solo modelos pequeños o mucha RAM)
- `8192` - Contexto muy largo, ~60GB+ RAM

**Impacto:**
- Mayor valor = Más contexto pero MÁS uso de RAM
- Menor valor = Menos contexto pero menos RAM

**Guía según tu RAM disponible:**
```bash
# Si tienes 16GB RAM total → usa 1024
OLLAMA_CONTEXT_LENGTH=1024

# Si tienes 32GB RAM total → usa 2048 (recomendado)
OLLAMA_CONTEXT_LENGTH=2048

# Si tienes 64GB+ RAM total → usa 4096
OLLAMA_CONTEXT_LENGTH=4096
```

### `LLM_TIMEOUT`
**Valor por defecto:** `120`
**Descripción:** Timeout para llamadas al LLM en segundos.

**Valores recomendados:**
- `60` - Rápido, cancela si tarda mucho
- `120` - Equilibrio (recomendado)
- `300` - Permisivo, para consultas muy complejas

---

## Sistema de Routing

### Cómo Funciona el Routing

El sistema utiliza **routing 100% LLM per-message** para clasificar automáticamente **CADA MENSAJE de forma INDEPENDIENTE**. Esto significa que el agente:

1. **Analiza SOLO el mensaje actual** (sin influencia del historial previo)
2. **Clasifica automáticamente** en una de dos categorías:
   - `vectorstore`: Necesita buscar en documentos de licitaciones
   - `general`: Conversación general sin necesidad de documentos
3. **Decide la ruta** según la clasificación del mensaje actual
4. **Cambia dinámicamente** entre rutas según cada nuevo mensaje

### Routing Per-Message (Independiente)

**Característica clave:** El routing clasifica cada mensaje individual, NO toda la conversación.

**Ejemplo de flujo multi-turno:**

```
Usuario: "hola"
→ Clasificación: general (sin documentos)
→ Respuesta: saludo cordial

Usuario: "cual es la mejor oferta en software"
→ Clasificación: vectorstore (busca documentos)
→ Respuesta: análisis de 6 licitaciones de software

Usuario: "gracias"
→ Clasificación: general (sin documentos)
→ Respuesta: despedida cordial

Usuario: "busca ofertas de construcción"
→ Clasificación: vectorstore (busca documentos)
→ Respuesta: análisis de licitaciones de construcción
```

**Ventajas del routing per-message:**
- ✅ **Cada mensaje se clasifica independientemente** - no hay sesgo del historial
- ✅ **Cambio dinámico de rutas** - puede alternar entre general/vectorstore libremente
- ✅ **Mucho más preciso** - "gracias" siempre es general, aunque el mensaje anterior fuera sobre licitaciones
- ✅ **Efectividad máxima** - cada pregunta obtiene el tratamiento correcto

**Ventajas del LLM routing:**
- ✅ Entiende **sinónimos automáticamente** ("licitaciones", "ofertas", "propuestas", "contratos")
- ✅ Detecta **intención** sin necesidad de keywords exactas
- ✅ Se **adapta a lenguaje natural** sin rigidez
- ✅ **Sin mantenimiento** - no requiere añadir keywords manualmente

**Ejemplos de clasificación:**
- "cual es la mejor oferta en software" → `vectorstore` (busca documentos)
- "busca propuestas de desarrollo web" → `vectorstore` (sinónimo detectado)
- "hola que tal" → `general` (saludo)
- "gracias" → `general` (despedida)
- "qué es una licitación pública" → `general` (pregunta conceptual)

### Uso del Historial

**Importante:** El historial de conversación se usa SOLO para generar respuestas contextua les, NO para clasificar.

- **Routing:** Clasifica solo el mensaje actual (sin historial)
- **Answer:** Usa el historial para dar respuestas con contexto conversacional

Esto garantiza que cada mensaje se clasifique correctamente mientras las respuestas mantienen coherencia conversacional.

**Configuración relacionada:**
El routing utiliza `LLM_TEMPERATURE` y `LLM_TIMEOUT` del `.env` para la clasificación.

---

## Características del Agente

### `USE_GRADING`
**Valor por defecto:** `True`
**Descripción:** Activar validación de relevancia de documentos recuperados.

**Opciones:**
- `True` - Valida documentos antes de usarlos (recomendado)
- `False` - Usa todos los documentos sin validar

**Impacto:**
- `True` = Respuestas más precisas, más lento
- `False` = Más rápido pero puede incluir info irrelevante

### `USE_XML_VERIFICATION`
**Valor por defecto:** `True`
**Descripción:** Activar verificación XML de campos críticos (presupuestos, fechas).

**Opciones:**
- `True` - Verifica campos críticos en XML (recomendado)
- `False` - No verifica

**Impacto:**
- `True` = Datos críticos 100% precisos
- `False` = Más rápido pero posibles imprecisiones

---

## Vectorstore

### `CHROMA_PERSIST_DIRECTORY`
**Valor por defecto:** `data/index/chroma`
**Descripción:** Directorio donde se guarda el índice ChromaDB.

### `CHROMA_COLLECTION_NAME`
**Valor por defecto:** `eforms_chunks`
**Descripción:** Nombre de la colección en ChromaDB.

---

## Límites de Rendimiento

### `MAX_AGENT_ITERATIONS`
**Valor por defecto:** `5`
**Descripción:** Máximo número de iteraciones del agente para evitar loops infinitos.

**Valores recomendados:**
- `3` - Rápido, solo para consultas simples
- `5` - Equilibrio (recomendado)
- `10` - Permite razonamiento complejo

---

## Ejemplos de Configuraciones

### Configuración para PC con 16GB RAM (Performance)
```bash
MAX_CONVERSATION_HISTORY=5
DEFAULT_K_RETRIEVE=3
MIN_SIMILARITY_SCORE=0.6
LLM_TEMPERATURE=0.3
OLLAMA_CONTEXT_LENGTH=1024
LLM_TIMEOUT=60
USE_GRADING=False
USE_XML_VERIFICATION=False
MAX_AGENT_ITERATIONS=3
```

### Configuración para PC con 32GB RAM (Balanced) ⭐ RECOMENDADO
```bash
MAX_CONVERSATION_HISTORY=10
DEFAULT_K_RETRIEVE=6
MIN_SIMILARITY_SCORE=0.5
LLM_TEMPERATURE=0.3
OLLAMA_CONTEXT_LENGTH=2048
LLM_TIMEOUT=120
USE_GRADING=True
USE_XML_VERIFICATION=True
MAX_AGENT_ITERATIONS=5
```

### Configuración para PC con 64GB+ RAM (Quality)
```bash
MAX_CONVERSATION_HISTORY=20
DEFAULT_K_RETRIEVE=10
MIN_SIMILARITY_SCORE=0.4
LLM_TEMPERATURE=0.3
OLLAMA_CONTEXT_LENGTH=4096
LLM_TIMEOUT=180
USE_GRADING=True
USE_XML_VERIFICATION=True
MAX_AGENT_ITERATIONS=10
```

### Configuración para Chat Creativo
```bash
MAX_CONVERSATION_HISTORY=15
DEFAULT_K_RETRIEVE=6
MIN_SIMILARITY_SCORE=0.5
LLM_TEMPERATURE=0.7  # Más creativo
OLLAMA_CONTEXT_LENGTH=2048
LLM_TIMEOUT=120
USE_GRADING=True
USE_XML_VERIFICATION=True
MAX_AGENT_ITERATIONS=5
```

---

## Cómo Aplicar Cambios

1. Abre el archivo `.env` en la raíz del proyecto
2. Modifica los valores que desees
3. Guarda el archivo
4. Django recargará automáticamente (auto-reload)
5. Los cambios se aplican inmediatamente en la siguiente consulta

**Nota:** Si el servidor Django no está corriendo, simplemente inícialo con:
```bash
python manage.py runserver 8001
```

---

## Solución de Problemas

### El chat se queda sin memoria
```bash
# Reduce el contexto de Ollama
OLLAMA_CONTEXT_LENGTH=1024

# Reduce el historial
MAX_CONVERSATION_HISTORY=5
```

### Las respuestas son demasiado lentas
```bash
# Reduce documentos recuperados
DEFAULT_K_RETRIEVE=3

# Desactiva grading
USE_GRADING=False

# Reduce timeout
LLM_TIMEOUT=60
```

### Las respuestas no son precisas
```bash
# Aumenta umbral de similaridad
MIN_SIMILARITY_SCORE=0.7

# Activa todas las verificaciones
USE_GRADING=True
USE_XML_VERIFICATION=True

# Aumenta documentos recuperados
DEFAULT_K_RETRIEVE=10
```

### El chat no recuerda conversaciones
```bash
# Aumenta historial
MAX_CONVERSATION_HISTORY=20
```

---

## Monitoreo

Para ver los valores actuales que está usando el agente, revisa los logs del servidor Django:

```bash
[SERVICE] Añadiendo historial de conversación (8 mensajes, límite: 10)...
```

Esto te muestra:
- Cuántos mensajes de historial se están usando
- Cuál es el límite configurado

---

## Preguntas Frecuentes

**Q: ¿Los cambios requieren reiniciar el servidor?**
A: No, Django auto-recarga cuando cambias el `.env`.

**Q: ¿Puedo tener diferentes configuraciones para diferentes usuarios?**
A: Actualmente no, las configuraciones son globales. Esta es una mejora futura posible.

**Q: ¿Qué pasa si pongo valores inválidos?**
A: El sistema usará los valores por defecto y puede mostrar errores en los logs.

**Q: ¿Cómo sé qué configuración es mejor para mí?**
A: Empieza con la configuración "Balanced" y ajusta según tu experiencia.

---

**Última actualización:** 18 de Octubre, 2025
