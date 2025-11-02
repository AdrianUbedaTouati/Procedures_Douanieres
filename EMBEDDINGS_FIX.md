# Fix: Modelo de Embeddings Inválido para OpenAI - v3.2.4

## 🎯 Problema Resuelto

### Error Crítico Identificado
```
HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 400 Bad Request"
ERROR: Error code: 400 - {'error': {'message': 'invalid model ID'}}
```

**Consecuencias:**
- Búsquedas retornaban 0 documentos
- Agent respondía "no se encontraron licitaciones" cuando SÍ había licitaciones
- Metadata mostraba `documents_used: []` siempre
- Panel de herramientas aparecía vacío

### Causa Raíz

El usuario configuraba **OpenAI como LLM provider**, pero el sistema usaba `user.ollama_embedding_model` para TODOS los providers, lo cual era incorrecto para OpenAI.

**Flujo erróneo**:
```
User Provider: openai
Embedding Model: nomic-embed-text (modelo de Ollama!)
    ↓
OpenAI API rechaza el modelo (400 Bad Request)
    ↓
Retriever retorna [] (empty list)
    ↓
Agent dice "no hay licitaciones"
```

## ✅ Solución Implementada

### Cambios Realizados

#### 1. Nuevo Campo en Modelo User

**Archivo**: `authentication/models.py`

**Añadido después de `openai_model`** (líneas 59-70):
```python
openai_embedding_model = models.CharField(
    max_length=100,
    blank=True,
    default='text-embedding-3-small',
    choices=[
        ('text-embedding-3-small', 'text-embedding-3-small (Económico, recomendado)'),
        ('text-embedding-3-large', 'text-embedding-3-large (Más preciso, más caro)'),
        ('text-embedding-ada-002', 'text-embedding-ada-002 (Legacy)'),
    ],
    verbose_name='Modelo Embeddings OpenAI',
    help_text='Modelo de embeddings para OpenAI (text-embedding-3-small recomendado)'
)
```

**Migración creada**: `authentication/migrations/0008_user_openai_embedding_model.py`

#### 2. Actualizar ChatAgentService

**Archivo**: `chat/services.py`

**Línea 29**: Añadido campo:
```python
self.openai_embedding_model = user.openai_embedding_model if hasattr(user, 'openai_embedding_model') else 'text-embedding-3-small'
```

**Líneas 77-90**: Lógica de selección de embedding model:
```python
# Crear retriever con el modelo de embeddings correcto según el provider
if self.provider == 'ollama':
    embedding_model = self.ollama_embedding_model
elif self.provider == 'openai':
    embedding_model = self.openai_embedding_model  # ← NUEVO
else:
    embedding_model = None  # Gemini u otros providers

retriever = create_retriever(
    k=6,
    provider=self.provider,
    api_key=None if self.provider == 'ollama' else self.api_key,
    embedding_model=embedding_model
)
```

#### 3. Fix Template de Tokens

**Archivo**: `chat/templates/chat/partials/_message_bubble.html`

**Línea 41**: Cambiada condición de `> 0` a `>= 0.0001`:
```django
{% if msg.metadata.total_tokens and msg.metadata.cost_eur >= 0.0001 %}
```

**Razón**: Costos muy pequeños (< €0.0001) no deben mostrar panel de pago.

## 🔄 Flujo Corregido

**Nuevo flujo correcto**:
```
User Provider: openai
    ↓
Seleccionar embedding model:
  - Si provider == 'openai' → user.openai_embedding_model ('text-embedding-3-small')
  - Si provider == 'ollama' → user.ollama_embedding_model ('nomic-embed-text')
  - Otros → None
    ↓
OpenAI API acepta el modelo (200 OK)
    ↓
Retriever retorna documentos relevantes
    ↓
Agent encuentra licitaciones y las muestra
```

## 📊 Modelos de Embeddings Disponibles

### OpenAI
| Modelo | Dimensiones | Costo (1M tokens) | Uso Recomendado |
|--------|-------------|-------------------|-----------------|
| `text-embedding-3-small` | 1536 | $0.02 | ✅ Recomendado (económico) |
| `text-embedding-3-large` | 3072 | $0.13 | Máxima precisión |
| `text-embedding-ada-002` | 1536 | $0.10 | Legacy (no recomendado) |

### Ollama (Local)
| Modelo | Dimensiones | Costo | Uso Recomendado |
|--------|-------------|-------|-----------------|
| `nomic-embed-text` | 768 | GRATIS | ✅ Recomendado |
| `mxbai-embed-large` | 1024 | GRATIS | Mayor precisión |
| `all-minilm` | 384 | GRATIS | Rápido |

## 🧪 Cómo Probar

### Test 1: Verificar Migración Aplicada

```bash
python manage.py shell -c "
from authentication.models import User
user = User.objects.first()
print(f'Has openai_embedding_model: {hasattr(user, \"openai_embedding_model\")}')
print(f'Value: {user.openai_embedding_model}')
"
```

**Resultado esperado**:
```
Has openai_embedding_model: True
Value: text-embedding-3-small
```

### Test 2: Búsqueda Funciona

1. Reiniciar servidor Django:
```bash
python manage.py runserver
```

2. Abrir sesión de chat nueva

3. Enviar mensaje:
```
Búscame licitaciones de software
```

4. **Verificar en logs del servidor**:
```
INFO: HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"  ← ✅
INFO: Recuperando documentos: query='software', k=6
INFO: search_tenders completado exitosamente
[SERVICE] Documentos recuperados: 3  ← ✅ (no 0)
```

5. **Verificar en respuesta**:
- Agent muestra licitaciones reales (con títulos, presupuestos, etc.)
- NO dice "no se encontraron licitaciones"

### Test 3: Metadata Completa Visible

**Verificar en la UI del mensaje**:

```
📄 3 documento(s) consultado(s)  ← ✅
🔧 Herramientas: search_tenders  ← ✅
💰 Tokens: 150 entrada + 75 salida = 225  ← ✅
💵 Coste: €0.0002 (aprox.)  ← ✅
```

### Test 4: Diferentes Providers

**Probar con Ollama**:
1. Cambiar provider en perfil a Ollama
2. Buscar licitaciones
3. Verificar que usa `nomic-embed-text`
4. Panel debe mostrar "100% GRATIS con Ollama"

**Probar con OpenAI**:
1. Cambiar provider a OpenAI
2. Buscar licitaciones
3. Verificar que usa `text-embedding-3-small`
4. Panel debe mostrar costo en EUR

## 🐛 Troubleshooting

### Problema 1: Migración No Aplicada

**Síntomas**: Error al acceder a `user.openai_embedding_model`

**Solución**:
```bash
python manage.py migrate authentication
```

### Problema 2: Usuario Sin Valor en openai_embedding_model

**Síntomas**: Campo existe pero está vacío

**Solución**:
```bash
python manage.py shell -c "
from authentication.models import User
user = User.objects.get(username='andri')
user.openai_embedding_model = 'text-embedding-3-small'
user.save()
print('✓ Modelo de embeddings configurado')
"
```

### Problema 3: Sigue Diciendo "No Hay Licitaciones"

**Verificar**:
1. ¿ChromaDB está inicializado?
```bash
python manage.py shell -c "
from tenders.vectorization_service import VectorizationService
from authentication.models import User
user = User.objects.first()
vs = VectorizationService(user=user)
status = vs.get_vectorstore_status()
print(f'Status: {status[\"status\"]}')
print(f'Collections: {status[\"collections_count\"]}')
print(f'Documents: {status[\"documents_count\"]}')
"
```

2. ¿El proveedor en perfil está bien configurado?

3. ¿La API key de OpenAI es válida?

### Problema 4: Panel de Tokens No Aparece

**Causas posibles**:
1. Metadata no tiene `total_tokens` → Ver logs del servidor
2. `cost_eur` es muy pequeño (< 0.0001) → Debería mostrar panel gratis
3. Mensajes antiguos (pre-fix) → Crear nueva sesión

## 📝 Modelos Recomendados Por Provider

### Para OpenAI ⭐
- **LLM**: `gpt-4o-mini` (balance calidad/precio)
- **Embeddings**: `text-embedding-3-small` (económico)

### Para Ollama ⭐
- **LLM**: `qwen2.5:72b` o `llama3.3:70b`
- **Embeddings**: `nomic-embed-text`

### Para Google Gemini ⭐
- **LLM**: `gemini-2.0-flash-exp`
- **Embeddings**: Usar el embedding de Gemini (automático)

## 📈 Impacto de los Cambios

### Búsquedas Funcionando
- ✅ Embedding requests exitosas (200 OK)
- ✅ Documentos relevantes retornados
- ✅ Agent responde con licitaciones reales

### Metadata Completa
- ✅ documents_used > 0
- ✅ tools_used visible
- ✅ Tokens y costo visible

### Costos
- OpenAI embedding: ~$0.00002 por búsqueda
- LLM OpenAI (gpt-4o-mini): ~€0.0002 por mensaje
- **Total**: ~€0.00022 por mensaje con búsqueda

---

**Fecha de Implementación**: 2025-11-02
**Versión**: 3.2.4
**Estado**: ✅ Implementado, migración aplicada
**Archivos Modificados**:
- [authentication/models.py](authentication/models.py:59-70)
- [authentication/migrations/0008_user_openai_embedding_model.py](authentication/migrations/0008_user_openai_embedding_model.py) (NUEVO)
- [chat/services.py](chat/services.py:29,77-90)
- [chat/templates/chat/partials/_message_bubble.html](chat/templates/chat/partials/_message_bubble.html:41)
