# Changelog

Todas las cambios notables en TenderAI Platform serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

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
