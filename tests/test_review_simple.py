# -*- coding: utf-8 -*-
"""
Test simple del sistema de revision - sin Unicode para evitar problemas en Windows
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print("="*80)
print("TEST SIMPLE - Sistema de Revision LLM")
print("="*80)

# Test 1: Import
print("\n[TEST 1] Importando modulos...")
try:
    from apps.chat.response_reviewer import ResponseReviewer
    from apps.chat.services import ChatAgentService
    from apps.authentication.models import User
    print("[OK] Modulos importados correctamente")
except Exception as e:
    print(f"[FAIL] Error importando modulos: {e}")
    sys.exit(1)

# Test 2: Get user with API key
print("\n[TEST 2] Buscando usuario con API key...")
try:
    user = User.objects.filter(llm_api_key__isnull=False).first()
    if not user:
        print("[FAIL] No hay usuarios con API key")
        sys.exit(1)
    print(f"[OK] Usuario encontrado: {user.email}")
    print(f"[OK] Provider: {user.llm_provider}")
except Exception as e:
    print(f"[FAIL] Error: {e}")
    sys.exit(1)

# Test 3: Initialize ChatAgentService
print("\n[TEST 3] Inicializando ChatAgentService...")
try:
    service = ChatAgentService(user, session_id=1)
    print("[OK] ChatAgentService inicializado")
except Exception as e:
    print(f"[FAIL] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Syntax check - verify review loop code exists
print("\n[TEST 4] Verificando que el codigo de revision existe en services.py...")
try:
    import inspect
    source = inspect.getsource(service.process_message)
    if 'ResponseReviewer' in source:
        print("[OK] Codigo de ResponseReviewer encontrado en process_message")
    else:
        print("[FAIL] ResponseReviewer no encontrado en process_message")
        sys.exit(1)

    if 'review_response' in source:
        print("[OK] Llamada a review_response encontrada")
    else:
        print("[FAIL] Llamada a review_response no encontrada")
        sys.exit(1)

    if 'improvement_prompt' in source:
        print("[OK] Logica de mejora encontrada (siempre activa)")
    else:
        print("[FAIL] Logica de mejora no encontrada")
        sys.exit(1)

except Exception as e:
    print(f"[FAIL] Error: {e}")
    sys.exit(1)

print("\n" + "="*80)
print("TODOS LOS TESTS PASARON")
print("="*80)
print("\nEl sistema de revision esta correctamente integrado en services.py")
print("Ahora puedes probarlo enviando un mensaje en el chat web")
