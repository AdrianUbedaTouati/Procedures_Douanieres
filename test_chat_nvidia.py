"""
Test chat service with NVIDIA integration
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
django.setup()

from django.contrib.auth import get_user_model
from chat.services import ChatAgentService

User = get_user_model()

print("="*70)
print("TEST CHAT SERVICE CON NVIDIA NIM")
print("="*70)

# Get user
user = User.objects.get(username='pepe2012')
print(f"\nUser: {user.username}")
print(f"Provider: {user.llm_provider}")
print(f"API Key: {user.llm_api_key[:20]}...")

# Create chat service
print("\n[1] Inicializando ChatAgentService...")
chat_service = ChatAgentService(user=user)
print("  ChatAgentService creado")

# Test questions
questions = [
    "¿Cuántas licitaciones hay disponibles?",
    "¿Qué licitaciones están relacionadas con software?",
    "¿Cuál es el presupuesto de las licitaciones?",
]

for i, question in enumerate(questions, 1):
    print(f"\n{'='*70}")
    print(f"[Q{i}] {question}")
    print("="*70)

    try:
        response = chat_service.process_message(question)

        print(f"\n[Respuesta]")
        print(response['content'])

        print(f"\n[Metadata]")
        metadata = response['metadata']
        print(f"  Route: {metadata.get('route', 'unknown')}")
        print(f"  Documents used: {metadata.get('num_documents', 0)}")
        print(f"  Iterations: {metadata.get('iterations', 0)}")

        if metadata.get('documents_used'):
            print(f"\n[Documentos Utilizados]")
            for j, doc in enumerate(metadata['documents_used'][:3], 1):
                print(f"  {j}. {doc['id']} [{doc['section']}]")
                print(f"     {doc['content_preview']}")

        if metadata.get('num_documents', 0) == 0:
            print(f"\n  [WARNING] No se recuperaron documentos!")
        else:
            print(f"\n  ✓ Chat funcionando correctamente!")

    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()

print("\n" + "="*70)
print("TEST COMPLETADO")
print("="*70)
