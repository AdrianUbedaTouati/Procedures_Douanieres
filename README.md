# TenderAI Platform v1.0.0

Plataforma inteligente de análisis de licitaciones públicas con IA integrada.

## 🚀 Características Principales

- **Recomendaciones IA**: Sistema de recomendaciones multicriteria usando Google Gemini
- **Chat Inteligente**: Asistente conversacional con RAG (Retrieval-Augmented Generation)
- **Gestión de Licitaciones**: Búsqueda, filtrado y seguimiento de ofertas públicas
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

### 4. Gestionar Licitaciones

- **Buscar**: Filtrar por texto, tipo de contrato, presupuesto
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
- **tenders**: CRUD de licitaciones, recomendaciones, búsqueda
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

## 📝 Notas de la Versión 1.0.0

### ✅ Implementado
- Sistema completo de autenticación
- Perfiles de empresa con 20+ campos
- Motor de recomendaciones IA
- Chat conversacional con RAG
- Gestión de licitaciones (CRUD)
- Admin interface completo
- Templates Bootstrap 5
- API key por usuario

### 🔜 Roadmap
- Importación masiva de XMLs TED
- Notificaciones por email
- Dashboard con gráficos
- Exportación de recomendaciones a PDF
- API REST para integraciones
- Sistema de suscripciones
- Mejoras en chunking y embeddings

## 🐛 Solución de Problemas

### Error: "No API key configurada"
- Verifica que hayas añadido tu API key en **Mi Perfil**

### Error al generar recomendaciones
- Asegúrate de que tu perfil de empresa esté completo
- Verifica que la API key sea válida

### Chat no responde
- Revisa que haya licitaciones indexadas en ChromaDB
- Verifica la conexión a internet

## 📄 Licencia

Proyecto privado - Todos los derechos reservados

## 👥 Equipo

Desarrollado con Django 5.2 + LangChain 0.3 + Google Gemini 2.5 Flash

---

**TenderAI Platform v1.0.0** - Encuentra las mejores oportunidades de licitación con IA
