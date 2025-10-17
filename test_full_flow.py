"""Test completo del flujo: Indexar + Chat con RAG"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
django.setup()

from django.contrib.auth import get_user_model
from tenders.vectorization_service import VectorizationService
from chat.services import ChatAgentService

User = get_user_model()

print("="*60)
print("TEST COMPLETO: INDEXAR + CHAT CON RAG")
print("="*60)

# 1. Obtener usuario
user = User.objects.filter(username='pepe2012').first()
if not user:
    print("[ERROR] Usuario pepe2012 no encontrado")
    exit(1)

print(f"\n[OK] Usuario: {user.username}")
print(f"  API Key: {user.llm_api_key[:20]}...")

# 2. Indexar licitaciones
print("\n" + "-"*60)
print("FASE 1: INDEXAR LICITACIONES EN CHROMADB")
print("-"*60)

vectorization_service = VectorizationService(user=user)

# Verificar estado inicial
status_before = vectorization_service.get_vectorstore_status()
print(f"\nEstado inicial:")
print(f"  - Chunks: {status_before.get('num_chunks', 0)}")

# Indexar
print("\nIndexando...")

def progress_callback(data):
    if data['type'] == 'progress':
        print(f"  [{data['current']}/{data['total']}] {data['tender_id']}")
    elif data['type'] == 'error':
        print(f"  [ERROR] {data['tender_id']}: {data['error']}")

try:
    result = vectorization_service.index_all_tenders(progress_callback=progress_callback)
    print(f"\n[OK] Indexacion completada!")

    if result.get('success'):
        print(f"  - Licitaciones indexadas: {result.get('indexed', 0)}")
        print(f"  - Total chunks: {result.get('total_chunks', 0)}")
        print(f"  - Errores: {result.get('errors', 0)}")
    else:
        print(f"  [ERROR] {result.get('error', 'Unknown error')}")
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 3. Probar Chat con RAG
print("\n" + "-"*60)
print("FASE 2: PROBAR CHAT IA CON RAG")
print("-"*60)

chat_service = ChatAgentService(user=user)

# Preguntas de prueba
questions = [
    "¿Cuántas licitaciones hay disponibles?",
    "¿Qué licitaciones están relacionadas con software o tecnología?",
]

for i, question in enumerate(questions, 1):
    print(f"\n[Q{i}] {question}")
    try:
        response = chat_service.process_message(question)
        print(f"[A{i}] {response['content'][:200]}...")
        print(f"  - Documentos usados: {response['metadata'].get('num_documents', 0)}")
        print(f"  - Ruta: {response['metadata'].get('route', 'unknown')}")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("TEST COMPLETADO")
print("="*60)
