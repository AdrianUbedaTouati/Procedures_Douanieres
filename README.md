# TenderAI Platform v1.4.0

Plataforma inteligente de análisis de licitaciones públicas con IA integrada y soporte para LLMs locales.

## 🚀 Características Principales

- **Chat Inteligente con Routing Per-Message**: Asistente conversacional con RAG (Retrieval-Augmented Generation)
  - **Sistema de routing 100% LLM** que clasifica cada mensaje de forma independiente
  - **Soporte multi-proveedor**: Google Gemini, OpenAI, NVIDIA, y **Ollama (100% local y gratis)**
  - **ChromaDB vectorstore** con 235+ documentos indexados
  - Cambio dinámico entre conversación general y consulta de documentos
- **Recomendaciones IA**: Sistema de recomendaciones multicriteria usando Google Gemini
- **Gestión de Licitaciones**: Búsqueda, filtrado y seguimiento de ofertas públicas
- **Descarga TED API**: Obtención automatizada de licitaciones europeas con progreso en tiempo real
- **Perfiles Empresariales**: Personalización completa para recomendaciones precisas
- **Análisis Multicriteria**: Evaluación técnica, presupuestaria, geográfica, de experiencia y competencia
- **100% Privado con Ollama**: Opción de usar modelos locales sin enviar datos a la nube

## 📋 Requisitos

- Python 3.10+
- Django 5.2.6
- **Opción 1 (Recomendado para privacidad)**: Ollama instalado localmente (100% gratis, sin API key)
- **Opción 2**: Google Gemini API Key / OpenAI API Key / NVIDIA API Key
- ChromaDB para vectorización
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

# Agent_IA Configuration
LLM_PROVIDER=google
DEFAULT_K_RETRIEVE=5
CHROMA_COLLECTION_NAME=licitaciones
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

### 3. Usar Chat IA

1. Ir a **Chat**
2. Click en **Nueva Conversación**
3. Hacer preguntas sobre licitaciones
4. Ejemplos:
   - "¿Qué licitaciones hay de desarrollo de software?"
   - "Dame detalles de la licitación 2024-123456"
   - "¿Cuáles son las fechas límite de esta semana?"

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

## 🤖 Sistema de Chat Inteligente

### Arquitectura RAG con Routing Per-Message

El chat utiliza un **sistema de routing 100% LLM** que analiza cada mensaje de forma independiente para decidir cómo responder.

#### Componentes Principales

**1. Routing Node (agent_ia_core/agent_graph.py)**
- Clasifica CADA mensaje individualmente (no toda la conversación)
- Usa solo el mensaje actual (sin influencia del historial)
- Decide entre dos rutas:
  - `vectorstore`: Consultar documentos de licitaciones
  - `general`: Conversación general sin documentos

**2. Retriever (agent_ia_core/retriever.py)**
- Recupera documentos relevantes de ChromaDB
- Embeddings con modelos específicos por proveedor:
  - **Ollama**: `nomic-embed-text` (local)
  - **Google**: `models/embedding-001`
  - **OpenAI**: `text-embedding-3-small`
  - **NVIDIA**: `nvidia/nv-embedqa-e5-v5`

**3. Answer Node (agent_ia_core/agent_graph.py)**
- Genera respuestas con contexto conversacional
- Usa el historial de conversación SOLO para respuestas, NO para routing
- Combina documentos recuperados + historial para respuestas coherentes

#### Flujo de una Conversación Multi-Turno

```
Usuario: "hola"
→ Routing: general (sin historial)
→ Respuesta: Saludo cordial

Usuario: "cual es la mejor licitación en software"
→ Routing: vectorstore (analiza SOLO este mensaje)
→ Recupera: 6 documentos relevantes de ChromaDB
→ Respuesta: Análisis detallado con datos de las licitaciones

Usuario: "gracias"
→ Routing: general (NO se confunde con el mensaje anterior!)
→ Respuesta: Despedida cordial
```

### Configuración del Agente

El agente es totalmente configurable vía `.env`:

```env
# Sistema de Routing (LLM-based)
LLM_TEMPERATURE=0.3              # Creatividad del LLM (0.0-1.0)
LLM_TIMEOUT=120                  # Timeout en segundos

# Recuperación de Documentos
DEFAULT_K_RETRIEVE=6             # Documentos a recuperar
MIN_SIMILARITY_SCORE=0.5         # Umbral de similitud (0.0-1.0)

# Características del Agente
USE_GRADING=True                 # Validar relevancia de docs
USE_XML_VERIFICATION=True        # Verificar campos críticos en XML

# Ollama Settings (local)
OLLAMA_CONTEXT_LENGTH=2048       # Contexto en tokens (1024/2048/4096)

# ChromaDB
CHROMA_COLLECTION_NAME=eforms_chunks
CHROMA_PERSIST_DIRECTORY=data/index/chroma

# Historial
MAX_CONVERSATION_HISTORY=10      # Límite de mensajes en contexto
```

Consulta [CONFIGURACION_AGENTE.md](CONFIGURACION_AGENTE.md) para detalles completos.

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

## 📝 Notas de la Versión 1.4.0

### ✨ Nuevo en v1.4.0 - Sistema de Chat Inteligente Completado

**Sistema de Routing Per-Message:**
- **Routing 100% LLM** que clasifica cada mensaje de forma independiente
- **Sin keywords rígidas**: El LLM entiende sinónimos e intención automáticamente
- **Cambio dinámico**: Alterna entre general/vectorstore según cada mensaje
- **Historial contextual**: Usado solo para respuestas, NO para clasificación
- **Testing completo**: 4/4 tests pasando en flujos multi-turno

**Integración Ollama (100% Local y Gratis):**
- Soporte completo para modelos Ollama (qwen2.5:7b, llama3.1, etc.)
- **Sin costos**: No se requiere API key ni pagos
- **100% Privado**: Todos los datos quedan en tu máquina
- ChromaDB con 235+ documentos indexados de 37 licitaciones
- Embeddings locales con `nomic-embed-text`

**Configuración Avanzada:**
- Sistema completamente configurable vía `.env`
- Archivo [CONFIGURACION_AGENTE.md](CONFIGURACION_AGENTE.md) con guía completa
- Settings de grading y verificación por usuario
- Control de context length, temperatura, timeout, etc.

**UI/UX Mejorada:**
- Diseño premium ultra-moderno para chat
- Gradientes vibrantes y animaciones suaves
- Markdown rendering con sintaxis highlight
- Citation badges con efectos de brillo
- Paneles de costos diferenciados (Ollama vs Cloud)

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

### 🔜 Roadmap
- Notificaciones por email cuando hay nuevas licitaciones
- Dashboard con gráficos y estadísticas
- Exportación de recomendaciones a PDF
- API REST para integraciones
- Sistema de suscripciones
- Indexación automática post-descarga
- Programación de descargas periódicas
- Soporte para más modelos Ollama (llama3.1, phi-3, etc.)
- Cache de embeddings para mayor velocidad
- Modo multi-agente para tareas complejas

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

### Chat General

**Chat no responde o no consulta documentos**
1. Verifica que haya licitaciones indexadas:
   - Ve a **/licitaciones/vectorizacion/**
   - Haz clic en "Indexar Todas las Licitaciones"
   - Espera a que termine (aparecerá mensaje de éxito)
2. Comprueba que ChromaDB tenga documentos:
   ```python
   python manage.py shell
   >>> import chromadb
   >>> client = chromadb.PersistentClient(path='data/index/chroma')
   >>> collection = client.get_collection('eforms_chunks')
   >>> print(collection.count())  # Debe mostrar 235+
   ```

**El routing no funciona correctamente**
- Verifica los logs del servidor (stderr)
- Busca líneas con `[ROUTE] Clasificando SOLO mensaje actual`
- Si usa keywords en lugar de LLM, el servidor no recargó los cambios

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

- **[CONFIGURACION_AGENTE.md](CONFIGURACION_AGENTE.md)** - Guía completa de configuración del agente RAG
- **[GUIA_INSTALACION_OLLAMA.md](GUIA_INSTALACION_OLLAMA.md)** - Instalación y configuración de Ollama
- **[ESTRUCTURA_PROYECTO.md](ESTRUCTURA_PROYECTO.md)** - Arquitectura y estructura del proyecto
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detalles técnicos de arquitectura
- **[CHANGELOG.md](CHANGELOG.md)** - Historial completo de cambios

---

**TenderAI Platform v1.4.0** - Encuentra las mejores oportunidades de licitación con IA

*Now with 100% local and free AI support via Ollama* 🚀
