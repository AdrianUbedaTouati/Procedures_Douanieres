# TenderAI Platform v3.7.0

Plataforma inteligente de análisis de licitaciones públicas con sistema de **Function Calling avanzado**, **Review Loop automático**, y navegación web interactiva con Playwright.

## 🚀 Características Principales

- **🤖 Sistema Function Calling con 16 Tools**: Agente IA que ejecuta herramientas especializadas automáticamente
  - **11 Tools siempre activas**: Context (2), Search (5), Info (2), Analysis (2)
  - **5 Tools opcionales**: Quality (2), Web (3) - incluye navegador interactivo Playwright
  - **Hasta 15 iteraciones automáticas** para resolver consultas complejas
  - **Review Loop automático** con ResponseReviewer que mejora TODAS las respuestas
- **🔍 Review Loop Automático v3.6+**: Sistema de mejora continua en 2 iteraciones
  - **Iteración 1**: Agent ejecuta tools y genera respuesta inicial
  - **Review**: ResponseReviewer evalúa formato (30%), contenido (40%), análisis (30%)
  - **Iteración 2**: SIEMPRE ejecutada con prompt mejorado basado en feedback
  - **Merge inteligente**: Combina documentos y herramientas de ambas iteraciones
- **🌐 Navegación Web Interactiva v3.7**: BrowseInteractiveTool con Playwright
  - **Navegador real Chromium** que ejecuta JavaScript completo
  - **Navegación inteligente con LLM**: Clicks, formularios, esperas dinámicas
  - **Ideal para portales complejos** como contrataciondelestado.es
  - Tasa de éxito 95-98% en sitios gubernamentales
- **🔍 Chat RAG Avanzado**: Retrieval-Augmented Generation con ChromaDB
  - **Soporte multi-proveedor**: Google Gemini, OpenAI, NVIDIA, Ollama (100% local y gratis)
  - **ChromaDB vectorstore** con embeddings especializados por proveedor
  - **Routing per-message** 100% LLM para decisiones inteligentes
- **📊 Recomendaciones IA Multicriteria**: Evaluación técnica, presupuestaria, geográfica
- **📥 Descarga TED API**: Obtención automatizada de licitaciones europeas con progreso en tiempo real
- **🏢 Perfiles Empresariales**: Autocompletado con IA desde texto libre
- **🔒 100% Privado con Ollama**: Opción de usar modelos locales sin enviar datos a la nube

## 📋 Requisitos

- Python 3.10+
- Django 5.2.6
- **Opción 1 (Recomendado para privacidad)**: Ollama instalado localmente (100% gratis, sin API key)
- **Opción 2**: Google Gemini API Key / OpenAI API Key / NVIDIA API Key
- ChromaDB para vectorización
- **Playwright** (opcional): Para navegación web interactiva
  ```bash
  pip install playwright
  playwright install chromium
  ```
- 16GB+ RAM para usar Ollama con modelos grandes

## 🛠️ Instalación

1. **Clonar repositorio**
```bash
git clone <repo-url>
cd TenderAI_Platform
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
Crea un archivo `.env` en la raíz del proyecto:
```
SECRET_KEY=tu-secret-key-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite por defecto)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Email (opcional para recuperación de contraseña)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Agent_IA Configuration - Function Calling v3.7
USE_FUNCTION_CALLING=true           # Activar sistema de Function Calling
LLM_PROVIDER=google                 # google | openai | ollama | nvidia
DEFAULT_K_RETRIEVE=6                # Documentos a recuperar
CHROMA_COLLECTION_NAME=eforms_chunks
LLM_TEMPERATURE=0.3                 # Creatividad (0.0-1.0)
MAX_FUNCTION_CALLING_ITERATIONS=15  # Máximo de iteraciones del agente

# ChromaDB Configuration
ANONYMIZED_TELEMETRY=False          # Deshabilita telemetría para evitar errores en logs
CHROMA_PERSIST_DIRECTORY=data/index/chroma
```

5. **Aplicar migraciones**
```bash
python manage.py migrate
```

6. **Crear superusuario**
```bash
python manage.py createsuperuser
```

7. **Ejecutar servidor**
```bash
python manage.py runserver
```

Accede a http://127.0.0.1:8000

## 🔑 Configuración de API Key

1. Obtén tu API key de Google Gemini: https://aistudio.google.com/app/apikey
2. Inicia sesión en TenderAI
3. Ve a **Mi Perfil** → **Editar Perfil**
4. En la sección **Configuración de IA**, ingresa tu API key
5. Guarda los cambios

## 📖 Guía de Uso

### 1. Configurar Perfil de Empresa

#### Opción A: Autocompletar con IA ⭐ (Recomendado)
1. Ir a **Mi Empresa**
2. En la sección "Autocompletar con IA", escribe un párrafo describiendo tu empresa
   - Incluye: nombre, sector, empleados, facturación, tecnologías, experiencia, ubicación, clientes
3. Click en **"Extraer Información con IA"**
4. La IA rellenará automáticamente los campos del formulario
5. Revisa y ajusta la información si es necesario
6. **Importante**: Marcar el perfil como completo

#### Opción B: Completar Manualmente
1. Ir a **Mi Empresa**
2. Completar toda la información:
   - Datos básicos (nombre, descripción, tamaño)
   - Capacidades técnicas (sectores, áreas técnicas)
   - Preferencias de licitación (CPV codes, tipos de contrato, presupuesto)
   - Experiencia y capacidades
3. **Importante**: Marcar el perfil como completo

### 2. Generar Recomendaciones

1. Ir a **Dashboard**
2. Click en **Generar Recomendaciones**
3. El sistema evaluará hasta 50 licitaciones activas
4. Ver recomendaciones en **Recomendadas**

### 3. Usar Chat IA con Function Calling

1. Ir a **Chat**
2. Click en **Nueva Conversación**
3. Hacer preguntas complejas - el agente usará las 16 tools automáticamente
4. **Ejemplos de consultas que ejecutan tools**:
   - "¿Qué licitaciones hay de desarrollo de software?" → `search_tenders`, `find_by_cpv`
   - "Dame las 3 mejores licitaciones de IT con presupuesto > 100k" → `find_by_cpv`, `find_by_budget`, `get_tender_details`
   - "Compara las licitaciones 123 y 456" → `compare_tenders`
   - "Busca en Google licitaciones de seguridad informática" → `web_search` (si `use_web_search=True`)
   - "Navega a contrataciondelestado.es y busca licitaciones recientes" → `browse_interactive` (Playwright)
5. **Review automático**: Todas las respuestas pasan por 2 iteraciones para máxima calidad

### 4. Descargar Licitaciones de TED API

1. Ir a **Licitaciones** → **Obtener desde TED**
2. **Precarga automática**: El formulario se rellena con tu perfil de empresa
   - Códigos CPV de tu sector
   - (Solo si es tu primera visita sin filtros activos)
3. Configurar o ajustar parámetros de búsqueda:
   - **Período**: Días hacia atrás (ej: 30 días)
   - **Máximo a descargar**: Límite de licitaciones (ej: 50)
   - **Códigos CPV**: Usa autocomplete con burbujas (ej: 7226 - Software)
   - **País/Región**: ESP, FRA, DEU, ITA, PRT, o todos
   - **Tipo de Aviso**: cn-standard, pin-only, can-standard
4. Click en **Iniciar Descarga**
5. Ver progreso en tiempo real:
   - Log estilo terminal con colores
   - Barra de progreso con porcentaje
   - Ventanas de fechas analizadas
   - Licitaciones encontradas y guardadas
   - **Botón "Cancelar Descarga"** para detener en cualquier momento
6. Esperar notificación de completado o cancelar si es necesario

**Características de la Descarga**:
- **Precarga inteligente** de datos del perfil de empresa
- **Cancelación en tiempo real** con botón dedicado
- **Filtros CPV múltiples** con precedencia correcta en queries
- Búsqueda por ventanas de fechas para evitar límites de API
- Detección automática de duplicados
- Progreso en tiempo real con Server-Sent Events (SSE)
- Log detallado en terminal del servidor
- Parseo y guardado automático en base de datos
- **Manejo robusto de errores** (DNS, conexión, HTTP 406)

### 5. Gestionar Licitaciones

- **Buscar**: Filtrar por CPV, NUTS, tipo de contrato, presupuesto, fechas
- **Guardar**: Marcar licitaciones de interés
- **Estados**: Interesado → Oferta Presentada → Ganada/Perdida

## 📁 Estructura del Proyecto

```
TenderAI_Platform/
├── TenderAI/              # Configuración principal
├── authentication/        # Sistema de usuarios
├── core/                  # Vistas base y perfil
├── company/              # Perfiles de empresa
├── tenders/              # Gestión de licitaciones
├── chat/                 # Chat con IA
├── agent_ia_core/        # Motor de IA (RAG + Recomendaciones)
├── templates/            # Templates HTML
├── static/               # Archivos estáticos
└── manage.py
```

## 🔧 Apps Django

- **authentication**: Registro, login, recuperación de contraseña
- **core**: Home, perfil de usuario
- **company**: Perfiles empresariales detallados
- **tenders**: CRUD de licitaciones, recomendaciones, búsqueda, descarga desde TED API
- **chat**: Sesiones de chat, integración con Agent_IA

## 🤖 Sistema de Chat Inteligente v3.7

### Arquitectura Function Calling con Review Loop

El chat utiliza un **sistema de Function Calling** donde el LLM decide automáticamente qué herramientas ejecutar para responder cada consulta.

#### Componentes Principales

**1. FunctionCallingAgent (agent_ia_core/agent_function_calling.py)**
- Ejecuta hasta **15 iteraciones automáticas**
- Decide qué tools llamar basándose en la consulta
- Ejecuta múltiples tools en paralelo cuando es posible
- Combina resultados de todas las tools para respuesta final

**2. ToolRegistry (agent_ia_core/tools/registry.py)**
- **16 tools especializadas**:
  - **Context (2)**: `get_company_info`, `get_tenders_summary`
  - **Search (5)**: `search_tenders`, `find_by_budget`, `find_by_deadline`, `find_by_cpv`, `find_by_location`
  - **Info (2)**: `get_tender_details`, `get_tender_xml`
  - **Analysis (2)**: `get_statistics`, `compare_tenders`
  - **Quality (2)**: `grade_documents`, `verify_fields` (opcional)
  - **Web (3)**: `web_search`, `browse_webpage`, `browse_interactive` (opcional)

**3. ResponseReviewer (chat/response_reviewer.py)** ⭐ NUEVO v3.6
- Evalúa TODAS las respuestas del agente
- Criterios de evaluación:
  - **Formato (30%)**: Markdown, estructura, claridad
  - **Contenido (40%)**: Completitud, datos esenciales
  - **Análisis (30%)**: Justificación, objetividad
- Proporciona feedback detallado y sugerencias de mejora

**4. Review Loop Automático** ⭐ NUEVO v3.6
```
1. ITERACIÓN INICIAL
   Agent ejecuta tools → Genera respuesta inicial

2. REVIEW (SIEMPRE ejecutado)
   ResponseReviewer analiza respuesta
   Detecta problemas y sugiere mejoras

3. SEGUNDA ITERACIÓN (SIEMPRE ejecutada)
   Prompt mejorado con feedback del reviewer
   Agent puede ejecutar tools adicionales si necesita
   Genera respuesta mejorada

4. MERGE Y RETORNO
   Respuesta final = iteración 2 (mejorada)
   Documentos = docs iteración 1 + docs iteración 2
```

**5. Retriever (agent_ia_core/retriever.py)**
- Recupera documentos relevantes de ChromaDB
- Embeddings especializados por proveedor:
  - **Ollama**: `nomic-embed-text` (local)
  - **Google**: `models/embedding-001`
  - **OpenAI**: `text-embedding-3-small`
  - **NVIDIA**: `nvidia/nv-embedqa-e5-v5`

**6. BrowseInteractiveTool (agent_ia_core/tools/browse_interactive_tool.py)** ⭐ NUEVO v3.7
- Navegador Chromium headless con Playwright
- Ejecuta JavaScript completo (SPA, React, Vue)
- **Modo inteligente con LLM**:
  1. Analiza página actual
  2. LLM decide: EXTRACT / CLICK / SEARCH
  3. Ejecuta acción (click, fill form, wait)
  4. Repite hasta encontrar información o max_steps
- Ideal para portales complejos (contrataciondelestado.es, PLACE, etc.)

#### Flujo de una Consulta con Function Calling

```
Usuario: "Dame las 3 mejores licitaciones de software con presupuesto > 50k"

→ ITERACIÓN 1:
  - Agent decide llamar: find_by_cpv(query="software")
  - Agent decide llamar: find_by_budget(min_budget=50000)
  - Agent combina resultados y genera respuesta inicial

→ REVIEW (SIEMPRE):
  - ResponseReviewer evalúa respuesta
  - Detecta: "Falta información de plazos de presentación"
  - Score: 75/100 (APPROVED, pero mejorable)
  - Sugerencia: "Añadir deadlines y contactos"

→ ITERACIÓN 2 (SIEMPRE):
  - Prompt mejorado: "Añade plazos y contactos a tu respuesta"
  - Agent llama: get_tender_details() para licitaciones seleccionadas
  - Genera respuesta MEJORADA con plazos, contactos, y análisis completo

→ MERGE:
  - Respuesta final = Iteración 2 (con plazos y contactos)
  - Documentos = docs de iteración 1 + docs de iteración 2
  - Metadata guardada: review_status, score, suggestions

→ USUARIO recibe respuesta de máxima calidad
```

### Configuración del Agente

El agente es totalmente configurable vía `.env`:

```env
# Function Calling System v3.7
USE_FUNCTION_CALLING=true                # Activar sistema de Function Calling
MAX_FUNCTION_CALLING_ITERATIONS=15       # Máximo de iteraciones automáticas
LLM_TEMPERATURE=0.3                      # Creatividad del LLM (0.0-1.0)
LLM_TIMEOUT=120                          # Timeout en segundos

# Recuperación de Documentos
DEFAULT_K_RETRIEVE=6                     # Documentos a recuperar
MIN_SIMILARITY_SCORE=0.5                 # Umbral de similitud (0.0-1.0)

# Características del Agente
USE_GRADING=false                        # ⚠️ Obsoleto en v3.0+ (usar tools opcionales)
USE_XML_VERIFICATION=false               # ⚠️ Obsoleto en v3.0+ (usar tools opcionales)

# Tools Opcionales (activar en perfil de usuario)
# use_web_search = True en el perfil → Activa web_search, browse_webpage, browse_interactive
# use_grading_docs = True en el perfil → Activa grade_documents
# use_field_verification = True en el perfil → Activa verify_fields

# Ollama Settings (local)
OLLAMA_CONTEXT_LENGTH=2048               # Contexto en tokens (1024/2048/4096)

# ChromaDB
CHROMA_COLLECTION_NAME=eforms_chunks
CHROMA_PERSIST_DIRECTORY=data/index/chroma

# Historial
MAX_CONVERSATION_HISTORY=10              # Límite de mensajes en contexto
```

**📖 Documentación completa**: Ver [CONFIGURACION_AGENTE.md](CONFIGURACION_AGENTE.md), [ARCHITECTURE.md](ARCHITECTURE.md), y [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md).

### Proveedores de LLM Soportados

| Proveedor | Modelos | API Key | Costo | Privacidad |
|-----------|---------|---------|-------|------------|
| **Ollama** | qwen2.5:7b, llama3.1, etc. | ❌ No necesita | 🆓 Gratis | ✅ 100% Local |
| Google Gemini | gemini-2.0-flash-exp | ✅ Sí | 💰 Pago | ⚠️ Cloud |
| OpenAI | gpt-4, gpt-3.5-turbo | ✅ Sí | 💰 Pago | ⚠️ Cloud |
| NVIDIA | mixtral-8x7b, etc. | ✅ Sí | 💰 Pago | ⚠️ Cloud |

**Recomendación**: Usa Ollama para máxima privacidad y costo cero.

### Recommendation Service
- Ubicación: `tenders/services.py`
- Funcionalidad: Evaluación multicriteria
- Dimensiones:
  1. Score Técnico (30%)
  2. Score Presupuesto (25%)
  3. Score Geográfico (20%)
  4. Score Experiencia (15%)
  5. Score Competencia (10%)

## 🗄️ Base de Datos

### Modelos Principales

**User** (authentication)
- Email único, API key del LLM
- Tracking de intentos de login

**CompanyProfile** (company)
- Perfil empresarial completo
- JSON fields para flexibilidad

**Tender** (tenders)
- Información de licitaciones
- CPV codes, NUTS regions
- Campos de contacto

**TenderRecommendation** (tenders)
- Puntuaciones multicriteria
- Nivel de recomendación
- Razones y advertencias

**ChatSession** y **ChatMessage** (chat)
- Historial de conversaciones
- Metadata de documentos usados

## 🔒 Seguridad

- Contraseñas hasheadas con PBKDF2
- Protección CSRF activada
- Rate limiting en login
- API keys por usuario (no compartidas)
- Sanitización de inputs

## 🚧 Desarrollo

### Crear migraciones
```bash
python manage.py makemigrations
python manage.py migrate
```

### Ejecutar tests
```bash
python manage.py test
```

### Colectar archivos estáticos
```bash
python manage.py collectstatic
```

## 🎨 Interfaz de Chat

El chat ha sido completamente rediseñado con un estilo minimalista inspirado en Apple:

- **Diseño Limpio**: Paleta de colores #007AFF, tipografía San Francisco
- **Animaciones Suaves**: Transiciones fluidas con cubic-bezier
- **AJAX sin Recargas**: Experiencia de usuario fluida
- **Auto-scroll Inteligente**: Scroll automático solo cuando es necesario
- **Typing Indicator**: Indicador animado mientras la IA responde
- **Metadata Visible**: Documentos consultados, tokens usados, ruta del agente
- **Responsive Design**: Adaptado para móvil, tablet y desktop
- **Dark Mode Ready**: Soporte automático para modo oscuro

### Archivos de Interfaz
```
static/
├── chat/
│   ├── css/chat.css       # Estilos Apple-inspired del chat
│   └── js/chat.js         # Interactividad AJAX y animaciones
└── core/
    ├── css/style.css      # Estilos globales
    └── js/main.js         # Utilidades generales
```

## 📝 Notas de la Versión 3.7.0

### ✨ Nuevo en v3.7.0 - BrowseInteractiveTool con Playwright

**Navegación Web Interactiva:**
- **Navegador Chromium headless** con Playwright
- **Ejecuta JavaScript completo** (SPA, React, Vue, Angular)
- **Modo inteligente con LLM**: Analiza página → Decide acción → Ejecuta → Repite
- **Acciones soportadas**: Click, fill forms, wait for content, scroll, navigate
- **Ideal para portales complejos**: contrataciondelestado.es, PLACE, etc.
- **95-98% success rate** en sitios gubernamentales
- **Activación**: `use_web_search=True` en perfil de usuario

**Ejemplo de uso**:
```python
Usuario: "Navega a contrataciondelestado.es y busca licitaciones recientes"
→ browse_interactive tool:
  1. Navega a URL
  2. LLM analiza página principal
  3. Decide hacer click en "Búsqueda"
  4. Llena formulario con criterios
  5. Envía y espera resultados
  6. Extrae información de licitaciones
  7. Retorna datos al agente
→ Respuesta final con licitaciones encontradas
```

### ✨ Incluido en v3.6.0 - Review Loop Automático

**Sistema de Mejora Continua:**
- **ResponseReviewer** evalúa TODAS las respuestas automáticamente
- **3 criterios de evaluación**: Formato (30%), Contenido (40%), Análisis (30%)
- **Segunda iteración SIEMPRE ejecutada** para mejorar respuestas
- **Feedback detallado**: Problemas detectados y sugerencias de mejora
- **Merge inteligente**: Combina documentos y tools de ambas iteraciones
- **Metadata guardada**: `review_status`, `review_score`, `review_issues`, `review_suggestions`

**Ejemplo de mejora**:
```
Iteración 1: "Estas son 3 licitaciones de software"
→ Review: "Falta información de plazos y contactos" (Score: 75/100)
→ Iteración 2: "Estas son 3 licitaciones de software:
   1. Licitación ABC - Plazo: 15/02/2025 - Contacto: xyz@email.com
   ..."
```

### ✨ Incluido en v3.0.0 - Sistema Function Calling Completo

**Function Calling con 16 Tools:**
- **11 tools siempre activas**: Context (2), Search (5), Info (2), Analysis (2)
- **5 tools opcionales**: Quality (2), Web (3)
- **Hasta 15 iteraciones automáticas** para resolver consultas complejas
- **Ejecución paralela** de tools cuando es posible
- **SchemaConverter automático** para cada proveedor LLM

**Tools disponibles**:
- **Context**: `get_company_info`, `get_tenders_summary`
- **Search**: `search_tenders`, `find_by_budget`, `find_by_deadline`, `find_by_cpv`, `find_by_location`
- **Info**: `get_tender_details`, `get_tender_xml`
- **Analysis**: `get_statistics`, `compare_tenders`
- **Quality** (opcional): `grade_documents`, `verify_fields`
- **Web** (opcional): `web_search`, `browse_webpage`, `browse_interactive`

### ✅ Incluido en v1.3.0
- **Cancelación de descargas en tiempo real** con botón dedicado
- **Precarga automática de datos** del perfil en formularios
- **Corrección de filtros CPV múltiples** con paréntesis correctos
- **Solución error HTTP 406** en descarga de XMLs
- **Persistencia de datos** en perfil de empresa
- Sistema de flags de cancelación por usuario thread-safe
- Headers anti-caché para datos siempre actualizados
- Logging mejorado con queries completas de TED API

### ✅ Implementado (versiones anteriores)
- Sistema completo de autenticación
- **Autocompletado de perfil de empresa con IA** (texto libre → campos estructurados)
- Perfiles de empresa con 20+ campos
- Motor de recomendaciones IA multicriteria
- **Chat estilo Apple con diseño minimalista**
- **Interfaz AJAX sin recargas**
- Gestión de licitaciones (CRUD)
- **Descarga automatizada desde TED API** con progreso en tiempo real (SSE)
- **Sistema de eliminación de licitaciones** (individual y masiva)
- **Autocompletado inteligente con burbujas** para CPV y NUTS
- **Búsqueda avanzada** con filtros CPV, NUTS, presupuesto, fechas
- **Filtros configurables** en descarga TED (CPV, país, tipo de aviso)
- **Manejo robusto de errores** de conexión con reintentos automáticos
- Admin interface completo
- Templates Bootstrap 5
- API key por usuario

### 🔜 Roadmap v4.0+
- **Multi-Agent Orchestration**: Coordinación de múltiples agentes especializados
- **Tool Learning**: Agentes que aprenden nuevas tools dinámicamente
- **Streaming de respuestas**: UI con respuestas en tiempo real (SSE/WebSocket)
- **Cache de Function Calls**: Reutilizar resultados de tools recientes
- **Notificaciones Push**: Email/SMS cuando hay nuevas licitaciones relevantes
- **Dashboard Analytics**: Gráficos de uso de tools, éxito de Function Calling
- **Exportación PDF mejorada**: Reportes con análisis de tools ejecutadas
- **API REST**: Endpoints para integración con sistemas externos
- **Playwright pool**: Pool de navegadores para mayor concurrencia

## 🐛 Solución de Problemas

### Chat con Ollama

**Error: "No se puede conectar con Ollama"**
1. Verifica que Ollama esté ejecutándose: `ollama serve`
2. Comprueba que esté en http://localhost:11434
3. Descarga el modelo: `ollama pull qwen2.5:7b`

**Error: "model requires more system memory"**
1. Usa un modelo más pequeño (ej: qwen2.5:7b en lugar de qwen2.5:72b)
2. Reduce `OLLAMA_CONTEXT_LENGTH` en `.env` (de 2048 a 1024)
3. Cierra otras aplicaciones para liberar RAM

**Chat muy lento con Ollama**
- Normal en la primera consulta (carga del modelo)
- Subsecuentes consultas son más rápidas (modelo en caché)
- Considera usar GPU si está disponible

### Chat con Proveedores Cloud

**Error: "No API key configurada"**
- Verifica que hayas añadido tu API key en **Mi Perfil** → **Editar Perfil**
- Selecciona el proveedor correcto (Google/OpenAI/NVIDIA)

**Error al generar recomendaciones**
- Asegúrate de que tu perfil de empresa esté completo
- Verifica que la API key sea válida

### Chat con Function Calling

**Chat no ejecuta tools**
1. Verifica que `USE_FUNCTION_CALLING=true` en `.env`
2. Verifica logs del servidor:
   - Busca `[FUNCTION CALLING] Initialized with X tools`
   - Debe mostrar las 16 tools (11 + 5 opcionales según perfil)
3. Comprueba que el usuario tenga API key configurada en perfil

**Review Loop no funciona**
1. Verifica logs del servidor:
   - Busca `[REVIEW] Analyzing response`
   - Busca `[IMPROVEMENT] Generating improved response`
2. El Review Loop requiere que `USE_FUNCTION_CALLING=true`
3. Verifica que ChatMessage tenga campos `review_*` en BD

**BrowseInteractiveTool no funciona**
1. Verifica que Playwright esté instalado:
   ```bash
   pip install playwright
   playwright install chromium
   ```
2. Verifica que `use_web_search=True` en perfil de usuario
3. Verifica logs: `[BROWSE INTERACTIVE] Navegando a URL`
4. En Windows, puede requerir ejecutar como administrador la primera vez

**Chat no consulta licitaciones indexadas**
1. Verifica que haya licitaciones indexadas:
   - Ve a **/licitaciones/vectorizacion/**
   - Haz clic en "Indexar Todas las Licitaciones"
2. Comprueba ChromaDB:
   ```python
   python manage.py shell
   >>> import chromadb
   >>> client = chromadb.PersistentClient(path='data/index/chroma')
   >>> collection = client.get_collection('eforms_chunks')
   >>> print(collection.count())  # Debe mostrar documentos
   ```
3. Con Function Calling, el agente decide si usar `search_tenders` tool
   - Verifica logs: `[AGENT] Calling tool: search_tenders`

### Problemas Generales

**CSS/JS no se cargan (imágenes vacías)**
1. Verifica que `DEBUG=True` en `.env`
2. Asegúrate de que Django esté instalado: `pip install django`
3. Los archivos estáticos deben estar en `static/chat/` y `static/core/`
4. Limpia caché del navegador: `Ctrl + Shift + R`
5. Reinicia el servidor

## 📄 Licencia

Proyecto privado - Todos los derechos reservados

## 👥 Equipo

Desarrollado con:
- **Backend**: Django 5.2.6 + Python 3.10+
- **IA/ML**: LangChain 0.3 + LangGraph + ChromaDB
- **LLMs**: Ollama (local) | Google Gemini 2.5 Flash | OpenAI | NVIDIA
- **Frontend**: Bootstrap 5 + JavaScript (AJAX)
- **Database**: SQLite (desarrollo) | PostgreSQL (producción)

---

## 📚 Documentación Adicional

**🎯 Empieza aquí:**
- **[DOCS_INDEX.md](DOCS_INDEX.md)** - Índice completo de documentación, guías por rol

**📖 Documentación principal:**
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Arquitectura completa del sistema v3.7
- **[TOOLS_REFERENCE.md](TOOLS_REFERENCE.md)** - Referencia completa de las 16 tools
- **[FLUJO_EJECUCION_CHAT.md](FLUJO_EJECUCION_CHAT.md)** - Flujo de ejecución paso a paso con Review Loop
- **[CONFIGURACION_AGENTE.md](CONFIGURACION_AGENTE.md)** - Configuración detallada del agente
- **[GUIA_INSTALACION_OLLAMA.md](GUIA_INSTALACION_OLLAMA.md)** - Instalación y configuración de Ollama

---

**TenderAI Platform v3.7.0** - Encuentra las mejores oportunidades de licitación con IA

*Powered by Function Calling, Review Loop, and Interactive Web Browsing* 🚀
