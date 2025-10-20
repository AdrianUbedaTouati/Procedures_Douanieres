"""
Script de diagnóstico para verificar el problema de sesión en login.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
django.setup()

from django.conf import settings
from django.contrib.sessions.models import Session
from authentication.models import User

print("="*80)
print("DIAGNÓSTICO DE SESIÓN Y LOGIN")
print("="*80)

# 1. Verificar configuración de sesión
print("\n[1] CONFIGURACIÓN DE SESIÓN:")
print(f"  SESSION_ENGINE: {settings.SESSION_ENGINE}")
print(f"  SESSION_COOKIE_AGE: {settings.SESSION_COOKIE_AGE}")
print(f"  SESSION_SAVE_EVERY_REQUEST: {settings.SESSION_SAVE_EVERY_REQUEST}")
print(f"  SESSION_COOKIE_HTTPONLY: {settings.SESSION_COOKIE_HTTPONLY}")
print(f"  SESSION_COOKIE_SAMESITE: {settings.SESSION_COOKIE_SAMESITE}")

# 2. Verificar configuración de autenticación
print("\n[2] CONFIGURACIÓN DE AUTENTICACIÓN:")
print(f"  AUTH_USER_MODEL: {settings.AUTH_USER_MODEL}")
print(f"  AUTHENTICATION_BACKENDS: {settings.AUTHENTICATION_BACKENDS}")
print(f"  LOGIN_URL: {settings.LOGIN_URL}")
print(f"  LOGIN_REDIRECT_URL: {settings.LOGIN_REDIRECT_URL}")

# 3. Verificar DEBUG y ALLOWED_HOSTS
print("\n[3] CONFIGURACIÓN DE DEBUG:")
print(f"  DEBUG: {settings.DEBUG}")
print(f"  ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")

# 4. Verificar middleware
print("\n[4] MIDDLEWARE:")
for middleware in settings.MIDDLEWARE:
    status = "✓" if "session" in middleware.lower() or "auth" in middleware.lower() else " "
    print(f"  [{status}] {middleware}")

# 5. Verificar sesiones en DB
print("\n[5] SESIONES EN BASE DE DATOS:")
try:
    total_sessions = Session.objects.count()
    print(f"  Total de sesiones: {total_sessions}")

    if total_sessions > 0:
        print("\n  Últimas 3 sesiones:")
        for session in Session.objects.all().order_by('-expire_date')[:3]:
            data = session.get_decoded()
            user_id = data.get('_auth_user_id', 'N/A')
            print(f"    - ID: {session.session_key[:10]}... | User ID: {user_id} | Expira: {session.expire_date}")
except Exception as e:
    print(f"  ❌ Error al consultar sesiones: {e}")

# 6. Verificar usuarios
print("\n[6] USUARIOS EN BASE DE DATOS:")
try:
    total_users = User.objects.count()
    print(f"  Total de usuarios: {total_users}")

    if total_users > 0:
        print("\n  Usuarios registrados:")
        for user in User.objects.all()[:5]:
            status = "Activo" if user.is_active else "Inactivo"
            verified = "Verificado" if user.email_verified else "Sin verificar"
            print(f"    - {user.username} ({user.email}) - {status} - {verified}")
except Exception as e:
    print(f"  ❌ Error al consultar usuarios: {e}")

# 7. Test de autenticación simulado
print("\n[7] TEST DE AUTENTICACIÓN SIMULADO:")
print("  (Simulando flujo de login sin crear sesión real)")
try:
    from django.contrib.auth import authenticate

    # Intentar con el primer usuario
    first_user = User.objects.first()
    if first_user:
        print(f"\n  Probando autenticación con: {first_user.username}")
        print(f"  ⚠️  NOTA: Necesitas saber la contraseña del usuario")
        print(f"  Si puedes, crea un usuario de prueba con: python manage.py createsuperuser")
    else:
        print(f"  ❌ No hay usuarios en la base de datos")
        print(f"  Crea uno con: python manage.py createsuperuser")

except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "="*80)
print("RECOMENDACIONES:")
print("="*80)

recommendations = []

if not settings.DEBUG:
    recommendations.append("⚠️  DEBUG está en False - Esto puede causar problemas en desarrollo")
    recommendations.append("   Solución: Asegúrate que .env tenga DEBUG=True")

if 'django.contrib.sessions.middleware.SessionMiddleware' not in settings.MIDDLEWARE:
    recommendations.append("❌ SessionMiddleware no está en MIDDLEWARE")
    recommendations.append("   Solución: Agrega 'django.contrib.sessions.middleware.SessionMiddleware' a MIDDLEWARE")

if 'django.contrib.auth.middleware.AuthenticationMiddleware' not in settings.MIDDLEWARE:
    recommendations.append("❌ AuthenticationMiddleware no está en MIDDLEWARE")

if not settings.SESSION_SAVE_EVERY_REQUEST:
    recommendations.append("⚠️  SESSION_SAVE_EVERY_REQUEST está en False")
    recommendations.append("   Solución: Agregar SESSION_SAVE_EVERY_REQUEST = True en settings.py")

if recommendations:
    for rec in recommendations:
        print(f"  {rec}")
else:
    print("  ✓ Todas las configuraciones básicas están correctas")
    print("\n  Si el login aún no funciona, intenta:")
    print("  1. Limpia cookies del navegador (Ctrl+Shift+Delete)")
    print("  2. Reinicia el servidor Django")
    print("  3. Verifica que el usuario existe y está activo")
    print("  4. Revisa los logs del servidor cuando intentas hacer login")

print("\n" + "="*80)
