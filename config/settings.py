"""
Django settings for Procédures Douanières project.
Solution d'Automatisation du Parcours Douanier - Corridor France ↔ Algérie
"""

from pathlib import Path
from decouple import config
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool, default=False)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Local apps
    'apps.authentication.apps.AuthenticationConfig',
    'apps.core.apps.CoreConfig',
    'apps.chat.apps.ChatConfig',
    'apps.expeditions.apps.ExpeditionsConfig',
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'data' / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'apps.authentication.validators.CustomPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'fr'

TIME_ZONE = 'Europe/Paris'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication
AUTH_USER_MODEL = 'apps_authentication.User'
LOGIN_URL = 'apps_authentication:login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'apps.authentication.backends.EmailOrUsernameBackend',
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

# Login Attempts Configuration
LOGIN_ATTEMPTS_ENABLED = config('LOGIN_ATTEMPTS_ENABLED', cast=bool, default=False)
MAX_LOGIN_ATTEMPTS = config('MAX_LOGIN_ATTEMPTS', cast=int, default=5)
LOGIN_COOLDOWN_MINUTES = config('LOGIN_COOLDOWN_MINUTES', cast=int, default=30)

# Email Verification Configuration
EMAIL_VERIFICATION_REQUIRED = config('EMAIL_VERIFICATION_REQUIRED', cast=bool, default=False)
SITE_URL = config('SITE_URL', default='http://localhost:8000')
EMAIL_VERIFICATION_COOLDOWN_SECONDS = config('EMAIL_VERIFICATION_COOLDOWN_SECONDS', cast=int, default=120)
PASSWORD_RESET_COOLDOWN_SECONDS = config('PASSWORD_RESET_COOLDOWN_SECONDS', cast=int, default=120)

# Agent_IA Configuration
LLM_PROVIDER = config('LLM_PROVIDER', default='google')
GOOGLE_API_KEY = config('GOOGLE_API_KEY', default='')
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
DEFAULT_K_RETRIEVE = config('DEFAULT_K_RETRIEVE', cast=int, default=6)
USE_GRADING = config('USE_GRADING', cast=bool, default=True)
USE_XML_VERIFICATION = config('USE_XML_VERIFICATION', cast=bool, default=True)

# ================================================
# CHROMADB CONFIGURATION
# ================================================
# Desactivar telemetría de ChromaDB para evitar errores de posthog
# y mejorar rendimiento (elimina latencia de timeouts de telemetría)
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
os.environ['CHROMA_TELEMETRY_ENABLED'] = 'False'

# Session Configuration
SESSION_COOKIE_AGE = 1209600  # 2 semanas
SESSION_SAVE_EVERY_REQUEST = False  # No es necesario guardar en cada request
SESSION_COOKIE_HTTPONLY = True  # Seguridad: cookies no accesibles desde JavaScript
SESSION_COOKIE_SAMESITE = 'Lax'  # Balance entre seguridad y funcionalidad
SESSION_COOKIE_SECURE = False  # False en desarrollo (HTTP sin SSL)
SESSION_COOKIE_NAME = 'sessionid'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Base de datos (estándar y confiable)

# CSRF Configuration
CSRF_COOKIE_SECURE = False  # False en desarrollo (HTTP sin SSL)
CSRF_COOKIE_SAMESITE = 'Lax'  # Balance entre seguridad y funcionalidad
