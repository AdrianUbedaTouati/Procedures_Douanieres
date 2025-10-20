"""
Script para probar el flujo completo de login y verificar cookies/sesión
"""
import sys
import os
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
django.setup()

from django.test import Client
from django.contrib.sessions.models import Session
from authentication.models import User

print("="*80)
print("TEST COMPLETO DE LOGIN - FLUJO REAL")
print("="*80)

# Crear cliente
client = Client()

# 1. Obtener usuario de prueba
user = User.objects.filter(email_verified=True, is_active=True).first()
if not user:
    print("\n[ERROR] No hay usuarios verificados y activos")
    print("Crea uno con: python manage.py createsuperuser")
    sys.exit(1)

print(f"\n[1] USUARIO DE PRUEBA")
print(f"    Username: {user.username}")
print(f"    Email: {user.email}")
print(f"    ID: {user.id}")

# 2. Contar sesiones antes
sessions_before = Session.objects.count()
print(f"\n[2] SESIONES EN DB ANTES DE LOGIN: {sessions_before}")

# 3. Hacer GET a /login/ para obtener CSRF token
print(f"\n[3] GET a /login/ para obtener CSRF token")
response = client.get('/login/')
print(f"    Status: {response.status_code}")
print(f"    Cookies: {list(client.cookies.keys())}")

# 4. Hacer POST a /login/ con credenciales
print(f"\n[4] POST a /login/ con credenciales")
print(f"    ⚠️ NOTA: Si el POST falla, es probable que la contraseña sea incorrecta")
print(f"    Puedes resetear la contraseña con:")
print(f"    python manage.py changepassword {user.username}")

# Intentar login (esto fallará si no sabemos la contraseña)
response = client.post('/login/', {
    'username': user.username,
    'password': 'testpass123',  # Cambiar por la contraseña real
    'remember_me': True
}, follow=False)  # No seguir redirect automáticamente

print(f"    Status: {response.status_code}")
print(f"    Redirect: {response.url if hasattr(response, 'url') else 'No redirect'}")
print(f"    Cookies después de POST: {list(client.cookies.keys())}")

# 5. Verificar sesión en cliente
print(f"\n[5] VERIFICAR SESIÓN EN CLIENTE")
if '_auth_user_id' in client.session:
    print(f"    ✅ Sesión creada!")
    print(f"    User ID en sesión: {client.session['_auth_user_id']}")
    print(f"    Session key: {client.session.session_key}")
else:
    print(f"    ❌ NO hay sesión en el cliente")
    print(f"    Contenido de sesión: {dict(client.session.items())}")

# 6. Contar sesiones después
sessions_after = Session.objects.count()
print(f"\n[6] SESIONES EN DB DESPUÉS DE LOGIN: {sessions_after}")
if sessions_after > sessions_before:
    print(f"    ✅ Se creó {sessions_after - sessions_before} sesión(es) nueva(s)")
    # Mostrar última sesión
    last_session = Session.objects.order_by('-expire_date').first()
    data = last_session.get_decoded()
    print(f"    User ID en última sesión: {data.get('_auth_user_id', 'N/A')}")
else:
    print(f"    ❌ NO se crearon sesiones nuevas")

# 7. Seguir redirect manualmente
if hasattr(response, 'url'):
    print(f"\n[7] SEGUIR REDIRECT MANUALMENTE a {response.url}")
    response2 = client.get(response.url)
    print(f"    Status: {response2.status_code}")

    # Verificar si la sesión persiste
    if '_auth_user_id' in client.session:
        print(f"    ✅ Sesión persiste después del redirect!")
        print(f"    User ID: {client.session['_auth_user_id']}")
    else:
        print(f"    ❌ Sesión se perdió después del redirect")

# 8. Test final: GET a home
print(f"\n[8] GET a /home/ (página de inicio)")
response3 = client.get('/')
print(f"    Status: {response3.status_code}")

if '_auth_user_id' in client.session:
    print(f"    ✅ Usuario sigue autenticado")
    print(f"    User ID: {client.session['_auth_user_id']}")
else:
    print(f"    ❌ Usuario NO está autenticado en home")

print("\n" + "="*80)
print("RESUMEN")
print("="*80)

if response.status_code == 302 and '_auth_user_id' in client.session:
    print("✅ LOGIN EXITOSO - Sesión funciona correctamente")
elif response.status_code == 400:
    print("❌ LOGIN FALLÓ - Verifica ALLOWED_HOSTS o credenciales")
elif response.status_code == 200:
    print("❌ LOGIN FALLÓ - Formulario no válido (contraseña incorrecta?)")
else:
    print(f"❌ LOGIN FALLÓ - Status code inesperado: {response.status_code}")

print("\n" + "="*80)
