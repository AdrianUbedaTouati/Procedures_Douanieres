# 🚀 Guía de Implementación - TenderAI Platform

Esta guía te llevará paso a paso para implementar la plataforma completa.

---

## ✅ FASE 1: Setup Inicial del Proyecto Django

### **Paso 1.1: Crear proyecto Django**

```bash
cd TenderAI_Platform

# Activar entorno virtual
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Instalar Django básico primero
pip install Django==5.2.6 python-decouple

# Crear proyecto Django
django-admin startproject TenderAI .

# Verificar que funciona
python manage.py runserver
```

### **Paso 1.2: Configurar settings.py base**

Editar `TenderAI/settings.py`:

```python
from pathlib import Path
from decouple import config
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', cast=bool, default=False)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps (añadir después)
    # 'rest_framework',
    # 'channels',

    # Local apps (crear después)
    # 'authentication',
    # 'core',
    # 'company',
    # 'tenders',
    # 'chat',
    # 'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'TenderAI.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Templates globales
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'TenderAI.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es'
TIME_ZONE = 'Europe/Madrid'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

### **Paso 1.3: Crear archivo .env**

```bash
cp .env.example .env
```

Editar `.env` con valores reales:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
GOOGLE_API_KEY=your-api-key
```

---

## ✅ FASE 2: App Authentication

### **Paso 2.1: Copiar app authentication desde BasePaginas**

```bash
# Copiar toda la carpeta authentication
cp -r ../BasePaginas/authentication ./
```

### **Paso 2.2: Actualizar settings.py**

```python
INSTALLED_APPS = [
    # ...
    'authentication.apps.AuthenticationConfig',
]

# Configuración de autenticación
AUTH_USER_MODEL = 'authentication.User'
LOGIN_URL = 'authentication:login'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

AUTHENTICATION_BACKENDS = [
    'authentication.backends.EmailOrUsernameBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', cast=int, default=587)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool, default=True)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@tenderai.com')

# Login Attempts
LOGIN_ATTEMPTS_ENABLED = config('LOGIN_ATTEMPTS_ENABLED', cast=bool, default=False)
MAX_LOGIN_ATTEMPTS = config('MAX_LOGIN_ATTEMPTS', cast=int, default=5)
LOGIN_COOLDOWN_MINUTES = config('LOGIN_COOLDOWN_MINUTES', cast=int, default=30)

# Email Verification
EMAIL_VERIFICATION_REQUIRED = config('EMAIL_VERIFICATION_REQUIRED', cast=bool, default=True)
SITE_URL = config('SITE_URL', default='http://localhost:8000')
```

### **Paso 2.3: Actualizar URLs**

Editar `TenderAI/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),
    # Otras URLs más adelante
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

### **Paso 2.4: Crear migraciones y migrar**

```bash
python manage.py makemigrations authentication
python manage.py migrate
python manage.py createsuperuser
```

### **Paso 2.5: Probar authentication**

```bash
python manage.py runserver
# Visitar http://localhost:8000/auth/login/
```

---

## ✅ FASE 3: App Core

### **Paso 3.1: Copiar app core desde BasePaginas**

```bash
cp -r ../BasePaginas/core ./
```

### **Paso 3.2: Actualizar templates base**

Editar `core/templates/core/base.html` para incluir:
- Logo TenderAI
- Menú de navegación adaptado (Dashboard, Licitaciones, Chat, Perfil)
- Estilos Bootstrap 5

### **Paso 3.3: Actualizar settings.py**

```python
INSTALLED_APPS = [
    # ...
    'authentication.apps.AuthenticationConfig',
    'core.apps.CoreConfig',
]

TEMPLATES[0]['OPTIONS']['context_processors'].append('core.context_processors.site_info')
```

### **Paso 3.4: Crear HomeView temporal**

Editar `core/views.py`:

```python
from django.views.generic import TemplateView

class HomeView(TemplateView):
    template_name = 'core/home.html'
```

Editar `core/urls.py`:

```python
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
]
```

Actualizar `TenderAI/urls.py`:

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),
    path('', include('core.urls')),  # Añadir esto
]
```

---

## ✅ FASE 4: App Company

### **Paso 4.1: Crear app company**

```bash
python manage.py startapp company
```

### **Paso 4.2: Crear modelo CompanyProfile**

Editar `company/models.py`:

```python
from django.db import models
from django.conf import settings

class CompanyProfile(models.Model):
    SIZE_CHOICES = [
        ('pequeña', 'Pequeña (1-50 empleados)'),
        ('mediana', 'Mediana (51-250 empleados)'),
        ('grande', 'Grande (250+ empleados)'),
    ]

    CAPACITY_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('buena', 'Buena'),
        ('alta', 'Alta'),
    ]

    RISK_CHOICES = [
        ('bajo', 'Bajo'),
        ('medio', 'Medio'),
        ('alto', 'Alto'),
    ]

    # Relación con User (OneToOne)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_profile'
    )

    # Company Info
    company_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sectors = models.JSONField(default=list)
    certifications = models.JSONField(default=list)
    size = models.CharField(max_length=20, choices=SIZE_CHOICES)
    annual_revenue_eur = models.IntegerField(null=True, blank=True)
    employees = models.IntegerField(null=True, blank=True)
    years_in_business = models.IntegerField(null=True, blank=True)
    geographic_presence = models.JSONField(default=list, help_text='NUTS regions')

    # Capabilities
    technical_areas = models.JSONField(default=list)
    programming_languages = models.JSONField(default=list)
    technologies = models.JSONField(default=list)
    certifications_technical = models.JSONField(default=list)

    # Experience
    relevant_projects = models.JSONField(default=list)
    public_sector_experience = models.BooleanField(default=False)
    previous_clients = models.JSONField(default=list)

    # Bidding Preferences
    preferred_cpv_codes = models.JSONField(default=list)
    preferred_contract_types = models.JSONField(default=list)
    budget_range = models.JSONField(
        default=dict,
        help_text='{"min_eur": 200000, "max_eur": 3000000}'
    )
    preferred_regions = models.JSONField(default=list)
    max_concurrent_bids = models.IntegerField(default=5)
    avoid_keywords = models.JSONField(default=list)

    # Competitive Analysis
    main_competitors = models.JSONField(default=list)
    competitive_advantages = models.JSONField(default=list)
    weaknesses = models.JSONField(default=list)

    # Risk Factors
    financial_capacity = models.CharField(max_length=20, choices=CAPACITY_CHOICES, default='media')
    team_availability = models.CharField(max_length=20, choices=CAPACITY_CHOICES, default='buena')
    overcommitment_risk = models.CharField(max_length=20, choices=RISK_CHOICES, default='bajo')

    # Metadata
    is_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil de Empresa'
        verbose_name_plural = 'Perfiles de Empresas'

    def __str__(self):
        return f"{self.company_name} ({self.user.email})"
```

### **Paso 4.3: Crear vistas y formularios**

Crear `company/forms.py`, `company/views.py`, `company/urls.py` (ver estructura en ARQUITECTURA_TECNICA.md)

### **Paso 4.4: Registrar en settings.py**

```python
INSTALLED_APPS = [
    # ...
    'company.apps.CompanyConfig',
]
```

### **Paso 4.5: Migrar**

```bash
python manage.py makemigrations company
python manage.py migrate
```

---

## ✅ FASE 5: Integrar Agent_IA Core

### **Paso 5.1: Copiar código de Agent_IA**

```bash
# Crear carpeta agent_ia_core
mkdir agent_ia_core
cd agent_ia_core

# Copiar archivos fuente desde Agent_IA/src/
cp ../Agent_IA/src/__init__.py ./
cp ../Agent_IA/src/config.py ./
cp ../Agent_IA/src/agent_graph.py ./
cp ../Agent_IA/src/retriever.py ./
cp ../Agent_IA/src/prompts.py ./
cp ../Agent_IA/src/tools_xml.py ./
cp ../Agent_IA/src/xml_parser.py ./
cp ../Agent_IA/src/chunking.py ./
cp ../Agent_IA/src/index_build.py ./
cp ../Agent_IA/src/recommendation_engine.py ./
cp ../Agent_IA/src/token_tracker.py ./
cp ../Agent_IA/src/ingest.py ./
cp ../Agent_IA/src/descarga_xml.py ./

# Copiar esquemas
mkdir schema
cp ../Agent_IA/schema/* ./schema/

# Copiar configs
mkdir config
cp ../Agent_IA/config/* ./config/
```

### **Paso 5.2: Adaptar config.py para Django**

Editar `agent_ia_core/config.py` para usar settings de Django:

```python
from django.conf import settings
from pathlib import Path

PROJECT_ROOT = settings.BASE_DIR
DATA_DIR = PROJECT_ROOT / "data"
XML_DIR = DATA_DIR / "xml"
RECORDS_DIR = DATA_DIR / "records"
INDEX_DIR = DATA_DIR / "index"
# ... resto igual
```

### **Paso 5.3: Crear directorios de datos**

```bash
mkdir -p data/xml data/records data/index/chroma
```

---

## ✅ FASE 6: App Tenders

### **Paso 6.1: Crear app tenders**

```bash
python manage.py startapp tenders
```

### **Paso 6.2: Crear modelos**

Editar `tenders/models.py` con los modelos `Tender`, `SavedTender`, `TenderSearch`, `TenderRecommendation` (ver ARQUITECTURA_TECNICA.md)

### **Paso 6.3: Crear servicios**

Crear `tenders/services.py`:

```python
from agent_ia_core import xml_parser, ingest, index_build, recommendation_engine

class TenderService:
    @staticmethod
    def download_tenders(days=7):
        # Llamar a descarga_xml.py
        pass

    @staticmethod
    def ingest_tenders():
        # Llamar a ingest.py → guardar en DB
        pass

    @staticmethod
    def build_index():
        # Llamar a index_build.py
        pass

    @staticmethod
    def generate_recommendations(user):
        # Llamar a recommendation_engine.py
        # Guardar en TenderRecommendation
        pass
```

### **Paso 6.4: Crear vistas**

Crear vistas para:
- `DashboardView`: TOP N recomendaciones
- `TenderListView`: Listado con filtros
- `TenderDetailView`: Detalle completo
- `TenderSearchView`: Búsqueda avanzada

### **Paso 6.5: Crear templates**

Crear templates Bootstrap 5 profesionales:
- `tenders/dashboard.html`
- `tenders/tender_list.html`
- `tenders/tender_detail.html`
- `tenders/search.html`

---

## ✅ FASE 7: App Chat

### **Paso 7.1: Crear app chat**

```bash
python manage.py startapp chat
```

### **Paso 7.2: Crear modelos**

Editar `chat/models.py` con `ChatSession`, `ChatMessage`

### **Paso 7.3: Crear interfaz con Agent_IA**

Crear `chat/agent_interface.py`:

```python
from agent_ia_core.agent_graph import EFormsRAGAgent

class AgentInterface:
    def __init__(self, user):
        self.user = user
        self.agent = EFormsRAGAgent(
            k_retrieve=6,
            use_grading=True,
            use_verification=True
        )

    def query(self, question):
        result = self.agent.query(question)
        return {
            'answer': result['answer'],
            'documents': result['documents'],
            'verified_fields': result['verified_fields'],
        }
```

### **Paso 7.4: Crear API REST**

Instalar DRF:

```bash
pip install djangorestframework
```

Crear `chat/serializers.py`, `chat/views.py` con ViewSets

### **Paso 7.5: Crear frontend de chat**

Crear modal de chat con JavaScript vanilla o Alpine.js

---

## ✅ FASE 8: Templates y Diseño

### **Paso 8.1: Instalar Bootstrap 5**

Descargar Bootstrap 5.3.0 o usar CDN en `core/templates/core/base.html`

### **Paso 8.2: Crear diseño profesional**

- **Navbar**: Logo + Menú (Dashboard, Licitaciones, Chat, Perfil)
- **Sidebar**: Filtros de búsqueda
- **Cards**: Para recomendaciones
- **Modals**: Para chat y detalles
- **Charts**: Chart.js para gráficos de compatibilidad

### **Paso 8.3: Añadir Alpine.js para reactividad**

```html
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
```

---

## ✅ FASE 9: Celery y Tareas Asíncronas

### **Paso 9.1: Instalar Celery y Redis**

```bash
pip install celery redis
```

### **Paso 9.2: Configurar Celery**

Crear `TenderAI/celery.py`

### **Paso 9.3: Crear tareas**

En `tenders/tasks.py`:

```python
from celery import shared_task
from .services import TenderService

@shared_task
def download_new_tenders_task():
    TenderService.download_tenders(days=1)
    TenderService.ingest_tenders()
    TenderService.build_index()

@shared_task
def generate_recommendations_task():
    # Para todos los usuarios
    pass
```

---

## ✅ FASE 10: Testing y Deploy

### **Paso 10.1: Crear tests**

```bash
pytest tests/
```

### **Paso 10.2: Configurar producción**

- PostgreSQL
- Gunicorn
- Nginx
- Supervisor (Celery workers)

### **Paso 10.3: Deploy a servidor**

Ver `docs/DEPLOYMENT_GUIDE.md` (crear)

---

## 📝 Checklist Final

- [ ] Todas las apps creadas y funcionando
- [ ] Modelos migrados
- [ ] Agent_IA integrado
- [ ] Templates profesionales con Bootstrap 5
- [ ] Chat funcionando
- [ ] Recomendaciones generándose correctamente
- [ ] Celery tasks programadas
- [ ] Tests pasando
- [ ] Documentación completa
- [ ] .env configurado para producción
- [ ] Deploy exitoso

---

## 🎯 Prioridades de Implementación

1. **CRÍTICO (Semana 1)**:
   - Authentication
   - Core
   - Company (sin wizard, formulario simple)
   - Agent_IA core integrado

2. **IMPORTANTE (Semana 2)**:
   - Tenders (modelos, servicios, vistas básicas)
   - Dashboard simple
   - Detalle de licitación

3. **DESEABLE (Semana 3)**:
   - Chat (versión simple sin WebSockets)
   - Recomendaciones
   - Templates mejorados

4. **FUTURO (Semana 4+)**:
   - Celery tasks
   - Notifications
   - WebSockets para chat
   - API REST completa

---

## 💡 Consejos

1. **Implementa iterativamente**: No intentes hacer todo a la vez
2. **Prueba cada fase**: Asegúrate de que funciona antes de continuar
3. **Commits frecuentes**: Git commit después de cada fase
4. **Documentación continua**: Actualiza README conforme avanzas
5. **Usa fixtures**: Crea datos de prueba con fixtures
6. **Debug toolbar**: Instala django-debug-toolbar desde el inicio

---

**¡Buena suerte con la implementación! 🚀**
