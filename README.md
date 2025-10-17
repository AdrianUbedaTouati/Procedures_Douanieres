# TenderAI Platform v1.2.0

Plataforma inteligente de análisis de licitaciones públicas con IA integrada.

## 🚀 Características Principales

- **Recomendaciones IA**: Sistema de recomendaciones multicriteria usando Google Gemini
- **Chat Inteligente**: Asistente conversacional con RAG (Retrieval-Augmented Generation)
- **Gestión de Licitaciones**: Búsqueda, filtrado y seguimiento de ofertas públicas
- **Descarga TED API**: Obtención automatizada de licitaciones europeas con progreso en tiempo real
- **Perfiles Empresariales**: Personalización completa para recomendaciones precisas
- **Análisis Multicriteria**: Evaluación técnica, presupuestaria, geográfica, de experiencia y competencia

## 📋 Requisitos

- Python 3.10+
- Django 5.2.6
- Google Gemini API Key
- ChromaDB para vectorización

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
2. Configurar parámetros de búsqueda:
   - **Período**: Días hacia atrás (ej: 30 días)
   - **Máximo a descargar**: Límite de licitaciones (ej: 50)
   - **Códigos CPV**: Códigos separados por coma (ej: 7226,7240)
   - **País/Región**: ESP, FRA, DEU, ITA, PRT, o todos
   - **Tipo de Aviso**: cn-standard, pin-only, can-standard
3. Click en **Iniciar Descarga**
4. Ver progreso en tiempo real:
   - Log estilo terminal con colores
   - Barra de progreso con porcentaje
   - Ventanas de fechas analizadas
   - Licitaciones encontradas y guardadas
5. Esperar notificación de completado

**Características de la Descarga**:
- Búsqueda por ventanas de fechas para evitar límites de API
- Detección automática de duplicados
- Progreso en tiempo real con Server-Sent Events (SSE)
- Log detallado en terminal del servidor
- Parseo y guardado automático en base de datos

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

## 🤖 Integración Agent_IA

### Chat Service
- Ubicación: `chat/services.py`
- Funcionalidad: RAG con LangChain + LangGraph
- Componentes: Route → Retrieve → Grade → Verify → Answer

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

## 📝 Notas de la Versión 1.2.0

### ✅ Implementado
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
- Mejoras en chunking y embeddings
- Indexación automática post-descarga
- Programación de descargas periódicas

## 🐛 Solución de Problemas

### Error: "No API key configurada"
- Verifica que hayas añadido tu API key en **Mi Perfil**

### Error al generar recomendaciones
- Asegúrate de que tu perfil de empresa esté completo
- Verifica que la API key sea válida

### Chat no responde
- Revisa que haya licitaciones indexadas en ChromaDB
- Verifica la conexión a internet

### CSS/JS no se cargan (imágenes vacías)
1. Verifica que `DEBUG=True` en `.env`
2. Asegúrate de que Django esté instalado: `pip install django`
3. Los archivos estáticos deben estar en `static/chat/` y `static/core/`
4. Limpia caché del navegador: `Ctrl + Shift + R`
5. Reinicia el servidor

## 📄 Licencia

Proyecto privado - Todos los derechos reservados

## 👥 Equipo

Desarrollado con Django 5.2 + LangChain 0.3 + Google Gemini 2.5 Flash

---

**TenderAI Platform v1.2.0** - Encuentra las mejores oportunidades de licitación con IA
