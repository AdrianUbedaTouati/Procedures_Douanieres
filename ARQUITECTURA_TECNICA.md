# 🏗️ Arquitectura Técnica - TenderAI Platform

**Versión:** 1.0.0
**Fecha:** 2025-10-14

---

## 📐 Visión General

TenderAI Platform es una aplicación web Django que integra un sistema RAG (Retrieval-Augmented Generation) basado en agentes para análisis inteligente de licitaciones públicas europeas.

### **Principios de Diseño**

1. **Modularidad**: Cada app Django es independiente y autosuficiente
2. **Escalabilidad**: Arquitectura preparada para crecimiento (Celery, Redis, PostgreSQL)
3. **Seguridad**: Autenticación robusta, validación de inputs, rate limiting
4. **Mantenibilidad**: Código limpio, bien documentado, con tests
5. **Performance**: Caché estratégico, índices vectoriales, consultas optimizadas

---

## 🎯 Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                        CAPA DE PRESENTACIÓN                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Templates   │  │  Static Files│  │  WebSockets  │          │
│  │  (Jinja2)    │  │  (Bootstrap) │  │  (Channels)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        CAPA DE APLICACIÓN                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Auth    │  │  Company │  │  Tenders │  │   Chat   │       │
│  │  Views   │  │  Views   │  │  Views   │  │  Views   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │            Agent_IA Core (RAG Engine)                │      │
│  │  route → retrieve → grade → verify → answer          │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        CAPA DE SERVICIOS                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  TED API     │  │  LLM APIs    │  │  Email       │         │
│  │  Integration │  │  (Gemini/GPT)│  │  Service     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │  Celery      │  │  Notification│                            │
│  │  Tasks       │  │  Service     │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        CAPA DE DATOS                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  PostgreSQL  │  │  ChromaDB    │  │  Redis       │         │
│  │  (Django ORM)│  │  (Vectors)   │  │  (Cache)     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐                                               │
│  │  File System │                                               │
│  │  (Media/XML) │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Aplicaciones Django (Apps)

### **1. authentication/** - Sistema de Autenticación

**Responsabilidad:** Gestión completa de usuarios y autenticación

**Modelos:**
```python
User(AbstractUser):
    - email (unique, USERNAME_FIELD)
    - email_verified
    - verification_token (UUID)
    - login_attempts
    - last_login_attempt
    - login_blocked_until
    - bio, avatar, phone
    - address_line1, city, postal_code, country

PasswordResetToken:
    - user (FK)
    - token (UUID)
    - created_at
    - used
```

**Vistas principales:**
- `LoginView`: Login con email o username
- `RegisterView`: Registro con verificación de email
- `VerifyEmailView`: Confirmación de email
- `PasswordResetView`: Recuperación de contraseña
- `ProfileView`: Ver y editar perfil

**Backend personalizado:**
```python
class EmailOrUsernameBackend(ModelBackend):
    """Permite login con email o username"""
    def authenticate(self, request, username=None, password=None):
        # Intenta con email primero, luego con username
```

---

### **2. core/** - Funcionalidades Base

**Responsabilidad:** Templates base, páginas estáticas, utilidades globales

**Vistas:**
- `HomeView`: Página de inicio
- `AboutView`: Sobre nosotros
- `ContactView`: Contacto
- `TermsView`: Términos y condiciones
- `PrivacyView`: Política de privacidad

**Templates base:**
- `base.html`: Template maestro
- `navbar.html`: Barra de navegación
- `footer.html`: Pie de página
- `messages.html`: Mensajes flash

**Context Processors:**
```python
def site_info(request):
    return {
        'SITE_NAME': 'TenderAI',
        'SITE_URL': settings.SITE_URL,
        'CURRENT_YEAR': datetime.now().year,
    }
```

---

### **3. company/** - Gestión de Perfil Empresarial

**Responsabilidad:** Configuración y gestión del perfil de empresa

**Modelos:**
```python
CompanyProfile:
    - user (OneToOne)
    - company_name
    - description
    - sectors (JSONField)
    - certifications (JSONField)
    - size (choices: pequeña, mediana, grande)
    - annual_revenue_eur
    - employees
    - years_in_business
    - geographic_presence (JSONField: NUTS regions)

    # Capabilities
    - technical_areas (JSONField)
    - programming_languages (JSONField)
    - technologies (JSONField)

    # Experience
    - relevant_projects (JSONField)
    - public_sector_experience (bool)
    - previous_clients (JSONField)

    # Bidding Preferences
    - preferred_cpv_codes (JSONField)
    - preferred_contract_types (JSONField)
    - budget_range (JSONField: min_eur, max_eur)
    - preferred_regions (JSONField: NUTS)
    - avoid_keywords (JSONField)

    # Competitive Analysis
    - competitive_advantages (JSONField)
    - weaknesses (JSONField)

    # Risk Factors
    - financial_capacity (choices)
    - team_availability (choices)
    - overcommitment_risk (choices)

    - created_at, updated_at
```

**Vistas:**
- `ProfileSetupView`: Wizard de configuración inicial (3 pasos)
- `ProfileEditView`: Edición de perfil
- `ProfileDetailView`: Vista detallada del perfil
- `ExportProfileView`: Exportar perfil a JSON

**Formularios:**
- `CompanyInfoForm`: Información básica
- `CapabilitiesForm`: Capacidades técnicas
- `PreferencesForm`: Preferencias de licitación
- `CompetitiveAnalysisForm`: Análisis competitivo

---

### **4. tenders/** - Gestión de Licitaciones

**Responsabilidad:** CRUD de licitaciones, búsqueda, recomendaciones

**Modelos:**
```python
Tender:
    - ojs_notice_id (unique)
    - title
    - description
    - short_description

    # Financial
    - budget_amount (Decimal)
    - currency (CharField, default='EUR')

    # Classification
    - cpv_codes (JSONField)
    - nuts_regions (JSONField)
    - contract_type (choices)

    # Buyer Information
    - buyer_name
    - buyer_type (choices)

    # Deadlines
    - publication_date
    - deadline (DateTimeField)
    - tender_deadline_date
    - tender_deadline_time

    # Procedure
    - procedure_type (choices: open, restricted, negotiated)
    - award_criteria (JSONField)

    # Contact
    - contact_email
    - contact_phone
    - contact_url

    # Source
    - xml_content (TextField)
    - source_path
    - xpaths_used (JSONField)

    # Metadata
    - indexed_at
    - views_count
    - created_at, updated_at

SavedTender:
    - user (FK)
    - tender (FK)
    - notes (TextField)
    - reminder_date (DateTimeField, null)
    - status (choices: interested, applied, won, lost)
    - saved_at

    Meta:
        unique_together = ['user', 'tender']

TenderSearch:
    - user (FK)
    - name (CharField)
    - filters (JSONField)
    - created_at
    - last_used_at

TenderRecommendation:
    - user (FK)
    - tender (FK)
    - score_total (Float)
    - score_technical (Float)
    - score_budget (Float)
    - score_geographic (Float)
    - score_experience (Float)
    - score_competition (Float)
    - probability_success (Float)
    - match_reasons (JSONField)
    - warning_factors (JSONField)
    - recommendation_level (choices: alta, media, baja)
    - generated_at

    Meta:
        unique_together = ['user', 'tender']
        ordering = ['-score_total']
```

**Vistas:**
- `DashboardView`: Dashboard principal con TOP N recomendaciones
- `TenderListView`: Listado de licitaciones con filtros
- `TenderDetailView`: Detalle completo de licitación
- `TenderSearchView`: Búsqueda avanzada
- `SavedTendersView`: Licitaciones guardadas
- `GenerateRecommendationsView`: Generar recomendaciones (POST)

**Servicios:**
```python
class TenderService:
    def download_tenders(days=7):
        """Descarga XMLs desde TED API"""

    def ingest_tenders():
        """Procesa XMLs → JSON → ChromaDB"""

    def generate_recommendations(user):
        """Genera recomendaciones para un usuario"""

    def search_tenders(query, filters):
        """Búsqueda híbrida (vectorial + filtros)"""
```

**Tasks (Celery):**
```python
@shared_task
def download_new_tenders_task():
    """Descarga nuevas licitaciones cada hora"""

@shared_task
def generate_all_recommendations_task():
    """Genera recomendaciones para todos los usuarios"""

@shared_task
def send_deadline_reminders_task():
    """Envía recordatorios de deadlines próximos"""
```

---

### **5. chat/** - Chatbot Inteligente

**Responsabilidad:** Interfaz de chat con Agent_IA

**Modelos:**
```python
ChatSession:
    - user (FK)
    - title (auto-generado del primer mensaje)
    - created_at
    - updated_at
    - is_archived

ChatMessage:
    - session (FK)
    - role (choices: user, assistant, system)
    - content (TextField)
    - metadata (JSONField):
        - documents_used (list)
        - verified_fields (list)
        - route (str)
        - tokens_used (int)
    - created_at

    Meta:
        ordering = ['created_at']
```

**Vistas:**
- `ChatSessionListView`: Lista de sesiones de chat
- `ChatSessionDetailView`: Vista de una sesión
- `ChatMessageCreateView`: Crear mensaje (AJAX/POST)
- `ChatSessionCreateView`: Nueva sesión de chat

**API Endpoints:**
```python
POST /api/chat/sessions/           # Crear nueva sesión
GET  /api/chat/sessions/           # Listar sesiones
GET  /api/chat/sessions/<id>/      # Detalle de sesión
POST /api/chat/sessions/<id>/messages/  # Enviar mensaje
GET  /api/chat/sessions/<id>/messages/  # Obtener mensajes
DELETE /api/chat/sessions/<id>/    # Eliminar sesión
```

**WebSocket Consumer (opcional):**
```python
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Conectar al canal del usuario

    async def receive(self, text_data):
        # Recibir mensaje, procesar con Agent_IA, enviar respuesta

    async def chat_message(self, event):
        # Enviar mensaje al WebSocket
```

**Interfaz con Agent_IA:**
```python
class AgentInterface:
    def __init__(self, user):
        self.user = user
        self.agent = EFormsRAGAgent(
            k_retrieve=6,
            use_grading=True,
            use_verification=True
        )

    def query(self, question):
        """Procesa consulta y retorna respuesta"""
        result = self.agent.query(question)
        return {
            'answer': result['answer'],
            'documents': result['documents'],
            'verified_fields': result['verified_fields'],
            'route': result['route'],
        }
```

---

### **6. notifications/** - Sistema de Notificaciones

**Responsabilidad:** Gestión de notificaciones y alertas

**Modelos:**
```python
Notification:
    - user (FK)
    - notification_type (choices: new_tender, deadline, recommendation)
    - title
    - message
    - tender (FK, null)
    - is_read
    - created_at

EmailAlert:
    - user (FK)
    - alert_type (choices: daily_digest, new_matches, deadline_reminder)
    - frequency (choices: immediate, daily, weekly)
    - filters (JSONField)
    - is_active
    - last_sent_at
    - created_at

NotificationPreferences:
    - user (OneToOne)
    - email_enabled
    - push_enabled
    - new_tenders_alert
    - deadline_alert
    - recommendation_alert
    - daily_digest
    - digest_time (TimeField, default='09:00')
```

**Servicios:**
```python
class NotificationService:
    def create_notification(user, type, title, message, tender=None):
        """Crea notificación"""

    def send_email_notification(user, subject, message):
        """Envía email"""

    def check_new_tenders(user):
        """Verifica nuevas licitaciones relevantes"""

    def send_daily_digest(user):
        """Envía resumen diario"""
```

---

### **7. agent_ia_core/** - Motor RAG

**Responsabilidad:** Lógica del sistema RAG (copiado de Agent_IA)

**Estructura:**
```
agent_ia_core/
├── __init__.py
├── config.py                    # Configuración del RAG
├── agent_graph.py               # Agente LangGraph
├── retriever.py                 # Retriever híbrido
├── prompts.py                   # Sistema de prompts
├── tools_xml.py                 # Herramientas de verificación
├── xml_parser.py                # Parser de eForms
├── chunking.py                  # División semántica
├── index_build.py               # Construcción de índice
├── recommendation_engine.py     # Motor de recomendaciones
└── token_tracker.py             # Tracking de tokens
```

**No es una app Django**, sino un módulo Python puro que se importa.

---

## 🔄 Flujos de Datos Principales

### **Flujo 1: Registro y Configuración**

```
1. Usuario visita /auth/register/
2. Completa formulario de registro
3. Sistema crea User (email_verified=False)
4. Se envía email con token de verificación
5. Usuario hace clic en link /auth/verify-email/<token>/
6. email_verified = True
7. Redirección a /company/profile/setup/
8. Wizard de 3 pasos para configurar CompanyProfile
9. Perfil completado → Redirección a /dashboard/
```

### **Flujo 2: Descarga e Ingesta de Licitaciones**

```
1. Celery task ejecuta cada hora: download_new_tenders_task()
2. Llama a TED API con filtros globales
3. Descarga XMLs → data/xml/
4. Ejecuta ingest_tenders():
   a. xml_parser.py → JSON normalizado
   b. Validación con Pydantic
   c. Guardar en PostgreSQL (Tender model)
5. Ejecuta build_index():
   a. chunking.py → Chunks semánticos
   b. Embeddings API → Vectores
   c. ChromaDB → Índice persistente
6. Ejecuta generate_all_recommendations_task():
   a. Para cada usuario activo:
   b. recommendation_engine.py → Scores
   c. Guardar en TenderRecommendation
7. Envía notificaciones a usuarios con nuevas matches
```

### **Flujo 3: Dashboard de Recomendaciones**

```
1. Usuario autenticado visita /dashboard/
2. Vista carga:
   a. TOP 5 TenderRecommendation (order_by='-score_total')
   b. Prefetch related Tender objects
3. Template renderiza:
   - Card por cada recomendación
   - Score total (0-100)
   - Desglose por categorías (gráfico radar)
   - Probabilidad de éxito
   - Match reasons (lista de puntos fuertes)
   - Warning factors (lista de advertencias)
   - Botones: Ver detalle, Guardar, Consultar en chat
```

### **Flujo 4: Chat con Agent_IA**

```
1. Usuario hace clic en icono de chat (bottom-right)
2. JavaScript abre modal de chat
3. Si no existe sesión activa:
   a. POST /api/chat/sessions/ → Crear ChatSession
4. Usuario escribe pregunta
5. JavaScript envía POST /api/chat/sessions/<id>/messages/
   {
     "content": "¿Cuál es el presupuesto de SAP?"
   }
6. Vista llama a AgentInterface.query():
   a. agent_graph.py ejecuta RAG flow
   b. route → retrieve → grade → verify → answer
   c. Retorna respuesta + metadatos
7. Vista guarda ChatMessage (role='user')
8. Vista guarda ChatMessage (role='assistant' con metadata)
9. Vista retorna JSON response
10. JavaScript renderiza respuesta en el chat
```

### **Flujo 5: Detalle de Licitación**

```
1. Usuario hace clic en licitación
2. Vista TenderDetailView:
   a. tender = get_object_or_404(Tender, ojs_notice_id=id)
   b. tender.increment_views()
   c. saved = SavedTender.objects.filter(user=user, tender=tender).exists()
   d. recommendation = TenderRecommendation.objects.get(user=user, tender=tender)
3. Template renderiza:
   - Encabezado con título y organismo
   - Tabs:
     * Información general (descripción, presupuesto, deadline)
     * Criterios de adjudicación (lista detallada)
     * Contacto (email, teléfono, URL)
     * Análisis de compatibilidad (si hay recommendation)
     * Documentos (link a TED)
   - Sidebar:
     * Score de compatibilidad
     * Botón "Guardar" / "Guardado"
     * Botón "Consultar en chat"
     * Botón "Exportar a PDF"
```

---

## 🗄️ Modelo de Base de Datos

### **Diagrama ER Simplificado**

```
User (authentication)
 ├─ CompanyProfile (company) [OneToOne]
 ├─ SavedTender (tenders) [ManyToMany through]
 ├─ TenderRecommendation (tenders) [ForeignKey]
 ├─ ChatSession (chat) [ForeignKey]
 ├─ Notification (notifications) [ForeignKey]
 └─ EmailAlert (notifications) [ForeignKey]

Tender (tenders)
 ├─ SavedTender [ManyToMany through]
 └─ TenderRecommendation [ForeignKey]

ChatSession (chat)
 └─ ChatMessage [ForeignKey]
```

### **Índices Importantes**

```python
# User
- email (unique)
- username (unique)

# CompanyProfile
- user (unique)

# Tender
- ojs_notice_id (unique)
- publication_date, deadline (for range queries)
- (cpv_codes, nuts_regions) - GIN index for JSONField

# TenderRecommendation
- (user, tender) (unique)
- (user, score_total) (for TOP N queries)

# SavedTender
- (user, tender) (unique)

# ChatMessage
- session, created_at (for ordering)
```

---

## 🚀 Despliegue y Escalabilidad

### **Desarrollo**
```
- Django runserver
- SQLite
- Console email backend
- ChromaDB local
- Sin Celery
```

### **Staging**
```
- Gunicorn + Nginx
- PostgreSQL
- SMTP real
- ChromaDB persistente
- Celery + Redis
- Sentry (error tracking)
```

### **Producción**
```
- Gunicorn + Nginx + load balancer
- PostgreSQL (RDS o managed)
- SES o SendGrid (email)
- ChromaDB en volumen persistente
- Celery + Redis Cluster
- Sentry + monitoring
- S3 para media files
- CDN para estáticos
```

### **Escalabilidad Horizontal**

1. **Web servers**: Múltiples instancias de Gunicorn detrás de load balancer
2. **Celery workers**: Múltiples workers para tareas en background
3. **Redis**: Redis Cluster para alta disponibilidad
4. **PostgreSQL**: Réplicas de lectura para queries pesadas
5. **ChromaDB**: Considerar migrar a Pinecone o Weaviate para producción

---

## 🔒 Seguridad

### **Autenticación**
- Django sessions con cookies seguras
- Argon2 para hashing de contraseñas
- Tokens UUID para verificación de email
- Rate limiting en API endpoints

### **Autorización**
- LoginRequiredMixin en vistas protegidas
- Permissions por modelo (Django perms)
- CompanyProfile completado requerido para ciertas vistas

### **Validación**
- Django forms con validación server-side
- CSRF protection habilitado
- XSS protection (templates auto-escape)
- SQL injection prevention (ORM)

### **API Security**
- DRF authentication classes
- Rate limiting (django-ratelimit)
- CORS configurado restrictivamente
- API keys para servicios externos

---

## 📈 Monitoreo y Logging

### **Logging**
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/tenderai.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {'level': 'INFO'},
        'tenders': {'level': 'DEBUG'},
        'chat': {'level': 'DEBUG'},
        'agent_ia_core': {'level': 'INFO'},
    },
}
```

### **Métricas**
- Sentry para tracking de errores
- Django Debug Toolbar (desarrollo)
- Custom metrics:
  * Tenders ingested per day
  * Chat messages per user
  * Recommendations generated
  * API response times

---

## 🧪 Testing

### **Estructura de Tests**
```
tests/
├── authentication/
│   ├── test_models.py
│   ├── test_views.py
│   └── test_forms.py
├── company/
│   └── ...
├── tenders/
│   ├── test_models.py
│   ├── test_services.py
│   └── test_views.py
├── chat/
│   └── ...
└── agent_ia_core/
    ├── test_agent.py
    ├── test_retriever.py
    └── test_recommendation_engine.py
```

### **Tipos de Tests**
1. **Unit tests**: Lógica de negocio, utilidades
2. **Integration tests**: Servicios, APIs externas (mocked)
3. **End-to-end tests**: Flujos completos de usuario
4. **Performance tests**: Queries lentas, carga de índice

---

## 📚 Documentación

### **Estructura de Docs**
```
docs/
├── README.md                    # Este documento
├── ARQUITECTURA_TECNICA.md      # Este documento
├── API_REFERENCE.md             # Referencia de API
├── DEPLOYMENT_GUIDE.md          # Guía de despliegue
├── USER_GUIDE.md                # Guía de usuario
└── DEVELOPMENT_GUIDE.md         # Guía para desarrolladores
```

---

**Última actualización:** 2025-10-14
**Versión:** 1.0.0
