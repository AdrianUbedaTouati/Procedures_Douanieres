"""
Django settings for TenderAI project.
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
    'authentication.apps.AuthenticationConfig',
    'core.apps.CoreConfig',
    'company.apps.CompanyConfig',
    'tenders.apps.TendersConfig',
    'chat.apps.ChatConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'core.middleware.ForceSessionMiddleware',  # NUEVO: Middleware personalizado para forzar sesión
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
        'DIRS': [BASE_DIR / 'templates'],
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


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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
        'NAME': 'authentication.validators.CustomPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es'

TIME_ZONE = 'Europe/Madrid'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if os.path.exists(BASE_DIR / 'static') else []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication
AUTH_USER_MODEL = 'authentication.User'
LOGIN_URL = 'authentication:login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Authentication backends
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

# Session Configuration
SESSION_COOKIE_AGE = 1209600  # 2 semanas
SESSION_SAVE_EVERY_REQUEST = True  # Guardar sesión en cada request
SESSION_COOKIE_HTTPONLY = False  # CAMBIO: False para debugging (permite JavaScript)
SESSION_COOKIE_SAMESITE = None  # CAMBIO: None para permitir cross-site (más permisivo)
SESSION_COOKIE_SECURE = False  # False en desarrollo (HTTP sin SSL)
SESSION_COOKIE_NAME = 'sessionid'
SESSION_COOKIE_DOMAIN = None  # Usar dominio actual
SESSION_COOKIE_PATH = '/'
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'  # CAMBIO: Usar cookies firmadas (no DB)

# CSRF Configuration (para compatibilidad con cookies de sesión)
CSRF_COOKIE_SECURE = False  # False en desarrollo
CSRF_COOKIE_SAMESITE = None  # CAMBIO: None para permitir cross-site
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8001', 'http://localhost:8001']  # NUEVO
