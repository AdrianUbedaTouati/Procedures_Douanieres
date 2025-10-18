# Changelog

Todas las cambios notables en TenderAI Platform serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [1.4.0] - 2025-10-19

### Añadido

- **Sistema de Routing Per-Message (100% LLM)**
  - Clasifica CADA mensaje de forma independiente (no toda la conversación)
  - Elimina dependencia de keywords rígidas
  - Usa solo el mensaje actual para routing, historial solo para respuestas
  - Permite cambio dinámico entre rutas (general ↔ vectorstore)
  - Testing completo: 4/4 tests pasando en flujos multi-turno
  - Archivo: `agent_ia_core/agent_graph.py` - Método `_route_node()`
  - Prompts mejorados en `agent_ia_core/prompts.py`

- **Configuración avanzada del agente vía .env**
  - `MAX_CONVERSATION_HISTORY`: Límite de mensajes en contexto (default: 10)
  - `LLM_TEMPERATURE`: Creatividad del LLM (default: 0.3)
  - `LLM_TIMEOUT`: Timeout para clasificación (default: 120s)
  - `DEFAULT_K_RETRIEVE`: Documentos a recuperar (default: 6)
  - `MIN_SIMILARITY_SCORE`: Umbral de similitud (default: 0.5)
  - `USE_GRADING`: Activar validación de relevancia (default: True)
  - `USE_XML_VERIFICATION`: Verificar campos críticos (default: True)
  - `OLLAMA_CONTEXT_LENGTH`: Context length para Ollama (default: 2048)
  - Documentación completa en `CONFIGURACION_AGENTE.md`

- **Settings de usuario para grading y verification**
  - Nuevos campos en modelo User: `use_grading`, `use_verification`
  - UI en perfil de usuario para configurar el agente
  - Cada usuario puede personalizar el comportamiento del agente
  - Archivo: `authentication/models.py`, `authentication/migrations/`

- **UI Premium para Chat**
  - Diseño ultra-moderno con gradientes púrpura
  - Burbujas de mensaje con efectos de luz y sombra
  - Avatares con halo animado al hover
  - Área de input con borde gradient y glow effect
  - Botón de enviar con animación de rotación y scale
  - Badges de citación con efecto shimmer
  - Paneles de costos diferenciados: verde (Ollama gratis) vs morado (pago)
  - Versión CSS/JS: 3.0 para forzar recarga
  - Archivo: `static/chat/css/chat.css`

- **Integración completa de Ollama para modelos LLM locales**
  - Soporte para ejecutar modelos de IA 100% locales sin API keys
  - Modelo recomendado: Qwen2.5 72B (calidad comparable a GPT-4)
  - Privacidad total: datos nunca salen de la máquina
  - Costo cero: sin límites ni cuotas de uso
  - Funcionamiento offline: no requiere internet

- **Nuevos campos en modelo User** (`authentication/models.py`)
  - `ollama_model`: Modelo de chat (ej: qwen2.5:72b, llama3.3:70b)
  - `ollama_embedding_model`: Modelo de embeddings (ej: nomic-embed-text)
  - Provider choice añadido: `('ollama', 'Ollama (Local)')`

- **Sistema de verificación Ollama** (`core/ollama_checker.py`)
  - `OllamaHealthChecker`: Clase completa de health check
  - Verificación de instalación y versión Ollama
  - Verificación de servidor en puerto 11434
  - Listado de modelos instalados con tamaños
  - Test de modelo en tiempo real
  - Detección automática en Windows (búsqueda en rutas comunes)

- **Página de verificación Ollama**
  - URL: `/ollama/check/` con UI visual
  - Estados con colores (verde/amarillo/rojo)
  - Lista de modelos instalados
  - Configuración actual del usuario
  - Recomendaciones contextuales
  - Instrucciones de solución de problemas

- **Script de instalación automática Windows** (`instalar_ollama.bat`)
  - Instalación con un click de Ollama
  - Descarga automática de Qwen2.5 72B (~41GB)
  - Descarga automática de nomic-embed-text (~274MB)
  - Verificación completa de instalación
  - Inicio automático del servidor

- **Configuración dinámica de modelos en perfil**
  - Endpoint API `/ollama/models/` para listar modelos instalados
  - Selects dinámicos en edit_profile.html
  - Carga automática vía AJAX
  - Separación entre modelos de chat y embeddings
  - Mensaje de recomendación para qwen2.5:72b

- **Documentación completa**
  - `GUIA_INSTALACION_OLLAMA.md`: Guía paso a paso
  - `ESTRUCTURA_PROYECTO.md`: Documento maestro del proyecto
  - Sección Ollama en `ARCHITECTURE.md`
  - Actualización de `INSTALACION.md` con opción Ollama

### Mejorado

- **Arquitectura del Agente RAG completamente reescrita**
  - `chat/services.py`: Mensaje puro para routing + historial separado
  - Logs descriptivos: "Mensaje puro (para routing)" vs "Historial: X mensajes"
  - El agente recibe `conversation_history` como parámetro independiente
  - Método `query()` actualizado con parámetro `conversation_history`

- **AgentState expandido** (`agent_ia_core/agent_graph.py`)
  - Nuevo campo: `conversation_history` para historial separado
  - Documentación mejorada: `question` es SOLO la pregunta actual
  - Función interna `build_context_with_history()` en answer node
  - Historial usado SOLO en respuestas, NO en routing

- **Prompts del sistema optimizados** (`agent_ia_core/prompts.py`)
  - `SYSTEM_PROMPT`: Conversación natural sin forzar temas
  - Reglas explícitas: "NO menciones licitaciones si no es relevante"
  - Ejemplos de uso correcto vs incorrecto
  - Adaptación al contexto conversacional

- **Sistema de indexación corregido** (`agent_ia_core/index_build.py`)
  - `get_vectorstore()` solo carga índices, NO construye automáticamente
  - RuntimeError descriptivo si el índice no existe
  - Mensaje con pasos claros para indexar desde UI Django
  - Elimina auto-construcción desde `data/records/` inexistente

- **Markdown rendering en chat** (`chat/templates/chat/session_detail.html`)
  - Librería `markdown` para formateo de respuestas
  - Syntax highlighting para bloques de código
  - Listas, negritas, cursivas renderizadas correctamente
  - Template tag personalizado: `{% load chat_extras %}`
  - Filtro `markdown_format` para conversión automática

- **Lista de conversaciones mejorada** (`chat/templates/chat/session_list.html`)
  - Cards con borde izquierdo gradient
  - Preview del último mensaje en cada card
  - Botón de eliminar con confirmación
  - Empty state con diseño elegante
  - Hover effects y animaciones suaves

- **Soporte multi-provider mejorado**
  - `agent_ia_core/agent_graph.py`: ChatOllama y OllamaEmbeddings
  - `agent_ia_core/llm_factory.py`: Factory methods para Ollama
  - `chat/services.py`: Detección automática de provider Ollama
  - `tenders/vectorization_service.py`: Indexación con embeddings Ollama
  - API key opcional para Ollama (no requerida)

- **Sistema de costos actualizado** (`core/token_pricing.py`)
  - Pricing para Ollama: €0.00 en todo
  - Nota especial: "Completamente GRATIS - Modelo local sin límites"
  - Tracking correcto para provider 'ollama'

- **Interfaz de usuario**
  - Campo API key se oculta cuando provider = 'ollama'
  - Ayuda contextual sobre modelos Ollama
  - Recomendación destacada de qwen2.5:72b
  - Links a página de verificación

### Corregido
- **Error de indexación ChromaDB**
  - Eliminado sistema de colección temporal
  - Indexación directa en colección final
  - Conversión explícita de chunk_index a string
  - Reset completo de ChromaDB ante corrupción
  - Solución a error KeyError '_type'

- **Detección de modelos Ollama**
  - Matching flexible de tags (qwen2.5:72b vs qwen2.5:latest)
  - Búsqueda en múltiples rutas Windows
  - Manejo correcto de modelo no encontrado

- **Template paths**
  - Corrección de 'base.html' → 'core/base.html'
  - Templates Ollama en directorio correcto

### Técnico
- **Dependencias actualizadas** (`requirements.txt`)
  - `langchain-ollama>=0.2.0,<1.0.0` (compatible con core 0.3.x)
  - Versiones compatibles sin conflictos
  - Rangos de versión en lugar de versiones exactas

- **Migraciones de base de datos**
  - Nueva migración para campos ollama_model y ollama_embedding_model
  - Valores por defecto: qwen2.5:72b y nomic-embed-text

- **Arquitectura de servicio**
  - Validación de API key: `if provider != 'ollama'`
  - Inicialización condicional de embeddings
  - Base URL configurable para Ollama (http://localhost:11434)

- **Sistema de health check**
  - Método `_get_ollama_command()` para detección Windows
  - Método `check_model_installed()` con matching flexible
  - Método `get_installed_models()` con parsing de `ollama list`
  - Método `full_health_check()` para verificación completa

### Modelos Soportados
**Chat Models:**
- qwen2.5:72b ⭐ (41GB) - Recomendado
- llama3.3:70b (40GB) - Alta calidad
- deepseek-r1:14b (9GB) - Especializado en razonamiento
- mistral:7b (4.1GB) - Rápido

**Embedding Models:**
- nomic-embed-text ⭐ (274MB) - Recomendado
- mxbai-embed-large (669MB) - Mejor en español

### Requisitos Hardware
**Para Qwen2.5 72B:**
- RAM: 32GB+
- GPU: NVIDIA RTX 5080 (16GB VRAM) o superior
- Disco: 50GB libres
- Rendimiento esperado (RTX 5080): 15-25 tokens/segundo

## [1.3.0] - 2025-10-17

### Añadido
- **Sistema de cancelación de descargas en tiempo real**
  - Botón "Cancelar Descarga" visible durante el proceso
  - Cancelación graceful que espera al XML actual antes de detener
  - Flag de cancelación por usuario (`_cancel_flags` en ted_downloader)
  - Funciones: `set_cancel_flag()`, `clear_cancel_flag()`, `should_cancel()`
  - Nueva vista: `CancelDownloadView` para manejar peticiones de cancelación
  - Endpoint: `/licitaciones/cancelar-descarga/`
  - Evento SSE `cancelled` con estadísticas finales
  - Confirmación de usuario antes de cancelar
  - Feedback visual: botón cambia a "Cancelando..." y se deshabilita
  - Mensaje en log: "🛑 DESCARGA CANCELADA POR EL USUARIO"

- **Precarga de datos del perfil de empresa**
  - Formulario de descarga ("Obtener") precarga códigos CPV del perfil
  - Formulario de búsqueda ("Buscar") precarga CPV, NUTS y presupuesto
  - Solo aplica cuando NO hay filtros activos (primera visita)
  - Evita caché de navegador con headers: `Cache-Control: no-cache`
  - Consulta directa a DB con `CompanyProfile.objects.get()` para datos frescos

### Mejorado
- **Corrección de filtros CPV múltiples en descarga TED**
  - Paréntesis automáticos en expresiones OR: `(classification-cpv=7226* or classification-cpv=4500*)`
  - Prevención de problemas de precedencia de operadores AND/OR
  - Query correcta: `notice-type=X and (cpv1 or cpv2) and place=Y`
  - Logging mejorado: muestra query final enviada a TED API

- **Solución de error 406 en descarga de XMLs**
  - Headers específicos para descarga: `Accept: application/xml, text/xml, */*`
  - User-Agent personalizado: `TenderAI-Platform/1.0 (Python requests)`
  - Parámetro `session` en `download_xml_content()` para reutilizar conexión
  - Manejo robusto de errores HTTP con raise_for_status()

- **Persistencia de datos en perfil de empresa**
  - Corrección de campos value en template: `{{ form.company_name }}` en lugar de `{{ form.company_name.value }}`
  - Nombre de empresa, descripción y empleados ahora persisten después de guardar
  - Eliminación de referencias obsoletas al campo `sectors` en services.py y views.py

### Corregido
- Error 406 "Not Acceptable" al descargar XMLs de TED
- Nombre de empresa desaparecía después de guardar el perfil
- Filtros CPV múltiples generaban queries incorrectas en TED API
- Datos del perfil no se actualizaban en formularios de descarga/búsqueda

### Técnico
- Sistema de flags thread-safe para cancelación por usuario
- Verificación de cancelación en cada iteración del bucle de descarga
- Event listener JavaScript con fetch API para cancelación
- Manejo de evento `cancelled` en SSE con estadísticas parciales
- Logging detallado: `[FILTROS APLICADOS]` y `[QUERY TED API]`
- Headers HTTP anti-caché en `DownloadTendersFormView.dispatch()`
- Función `download_xml_content()` acepta sesión opcional para reutilización

## [1.2.0] - 2025-10-17

### Añadido
- **Sistema de eliminación de licitaciones**
  - Botón "Borrar Todos los XMLs" en página de obtener con confirmación
  - Botones individuales de eliminación en cada licitación del listado
  - Endpoints: `DeleteAllXMLsView` y `DeleteXMLView`
  - Confirmaciones antes de eliminar con contador de elementos
  - Recarga automática después de eliminación exitosa

- **Autocompletado inteligente con burbujas (tags)**
  - Sistema de autocomplete para códigos CPV en formulario de descarga
  - Búsqueda en tiempo real con debounce de 300ms
  - Muestra código y nombre del sector (ej: "7226 - Software")
  - Navegación con teclado (flechas, Enter, Escape, Backspace)
  - Sugerencias por defecto al hacer focus
  - Prevención de duplicados automática

- **Autocomplete mejorado en perfil de empresa**
  - Campo "Códigos CPV de interés (Sectores)" con autocomplete
  - Campo "Regiones NUTS" con autocomplete
  - Burbujas visuales que muestran código - nombre
  - Dropdown se mantiene abierto para agregar múltiples elementos
  - Click fuera del dropdown para cerrar
  - Integración con APIs `/empresa/api/autocomplete/cpv/` y `/empresa/api/autocomplete/nuts/`

- **Script de diagnóstico de conexión**
  - `test_ted_connection.py` para verificar conectividad con TED API
  - Tests de resolución DNS, conectividad básica, endpoints API
  - Verificación de configuración de proxy
  - Salida UTF-8 compatible con Windows

### Mejorado
- **Manejo de errores de conexión en TED API**
  - Sistema de reintentos automáticos con exponential backoff
  - Clase `create_session_with_retries()` con HTTPAdapter y Retry
  - Mensajes de error más descriptivos para problemas de DNS/conexión
  - Manejo robusto de errores de red con ConnectionError personalizado
  - Headers personalizados en requests (User-Agent)

- **Interfaz de usuario**
  - Tags/burbujas se despliegan en línea horizontal (flex-wrap)
  - Mejor posicionamiento del dropdown autocomplete (absolute positioning)
  - Estilos consistentes entre formularios de descarga, listado y perfil
  - Eliminado campo redundante "Sectores" del perfil (ahora es "Códigos CPV de interés (Sectores)")

### Corregido
- Error de duplicación en tags por defecto (mostraba "7226 - 7226" en lugar de "7226 - Software")
- Método `loadTagName()` ahora carga nombres desde API para tags iniciales
- Dropdown de autocomplete ahora se cierra correctamente con click fuera
- Prevención de blur en input al hacer click en dropdown (mousedown preventDefault)

### Técnico
- Importaciones añadidas: `HTTPAdapter`, `Retry` de requests/urllib3
- Configuración de reintentos: `MAX_RETRIES=3`, `BACKOFF_FACTOR=2`
- Status codes para retry: `[429, 500, 502, 503, 504]`
- Clase `AutocompleteTagsInput` reutilizable en múltiples formularios
- Eventos: `mousedown`, `focus`, `blur`, `click outside`
- Almacenamiento en hidden input como JSON array de códigos

## [1.1.0] - 2025-10-16

### Añadido
- **Sistema de descarga automatizada desde TED API**
  - Interfaz de configuración con parámetros personalizables
  - Filtros de búsqueda: CPV codes, país/región (PLACE), tipo de aviso (NOTICE_TYPE)
  - Progreso en tiempo real con Server-Sent Events (SSE)
  - Log estilo terminal con colores y emojis
  - Barra de progreso visual con porcentaje y contador
  - Búsqueda por ventanas de fechas para evitar límites de API
  - Detección automática de duplicados
  - Parseo y guardado automático en base de datos

- **Servicio TED Downloader** (`tenders/ted_downloader.py`)
  - `search_tenders_by_date_windows()` - Búsqueda inteligente por períodos
  - `download_and_save_tenders()` - Descarga y almacenamiento
  - Sistema de callbacks para reportar progreso
  - Integración con API TED v3

- **Vistas de descarga**
  - `DownloadTendersFormView` - Formulario de configuración
  - `DownloadTendersExecuteView` - Endpoint SSE con streaming en tiempo real
  - Thread separado para descarga sin bloquear la interfaz
  - Queue-based communication entre thread y SSE

- **Template de descarga** (`tender_download.html`)
  - Formulario con filtros CPV, PLACE, NOTICE_TYPE
  - Panel de progreso oculto que se muestra al iniciar
  - Log terminal con auto-scroll
  - Indicadores visuales (⏳ → 🔍 → ⬇️ → 🎉)
  - Manejo de eventos SSE con JavaScript EventSource

### Mejorado
- **Búsqueda de licitaciones**
  - Filtros avanzados: CPV codes, NUTS regions, presupuesto, fechas
  - Autocompletado de CPV y NUTS con AJAX
  - Validación de rangos de presupuesto y fechas
  - Mensajes informativos cuando no hay resultados

- **Logging y debugging**
  - Logs detallados en stderr para todas las operaciones de descarga
  - Prefijos [DOWNLOAD START], [SSE], [CALLBACK], [THREAD] para claridad
  - Información de parámetros en cada descarga

### Técnico
- Uso de `StreamingHttpResponse` para SSE
- Serialización JSON personalizada para objetos date/datetime
- Manejo de heartbeat para mantener conexión SSE viva
- Thread daemon para descargas en background
- Error handling robusto en descarga y parseo

## [1.0.0] - 2025-10-15

### Añadido
- Lanzamiento inicial de TenderAI Platform
- Sistema de autenticación completo
- Perfiles de empresa con autocompletado IA
- Motor de recomendaciones multicriteria
- Chat inteligente con RAG
- Gestión CRUD de licitaciones
- Integración con Google Gemini
- Admin interface configurado
- Templates Bootstrap 5 responsivos

### Apps Implementadas
- `authentication` - Login, registro, recuperación de contraseña
- `core` - Home, perfil de usuario
- `company` - Perfiles empresariales detallados
- `tenders` - Gestión de licitaciones y recomendaciones
- `chat` - Sesiones de chat con IA

### Servicios de IA
- `ChatAgentService` - RAG con LangChain + LangGraph
- `TenderRecommendationService` - Evaluación multicriteria
- `CompanyProfileAIService` - Extracción de información empresarial
- `TenderIndexingService` - Indexación en ChromaDB

---

## Tipos de Cambios
- **Añadido**: Para nuevas características
- **Cambiado**: Para cambios en funcionalidad existente
- **Deprecado**: Para características que serán eliminadas
- **Eliminado**: Para características eliminadas
- **Corregido**: Para corrección de bugs
- **Seguridad**: En caso de vulnerabilidades
- **Mejorado**: Para mejoras en rendimiento o UX
- **Técnico**: Para cambios técnicos internos
