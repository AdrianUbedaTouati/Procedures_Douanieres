"""
Test completo del sistema TenderAI con NVIDIA NIM
Verifica: Configuración -> Indexación -> Retrieval -> Chat
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
django.setup()

from django.contrib.auth import get_user_model
from tenders.models import Tender
from tenders.vectorization_service import VectorizationService
from chat.services import ChatAgentService
import shutil
from pathlib import Path

User = get_user_model()

print("="*70)
print("TEST COMPLETO: TENDERAI PLATFORM CON NVIDIA NIM")
print("="*70)

# FASE 0: Verificar usuario y configuración
print("\n[FASE 0] Verificando configuración...")
user = User.objects.get(username='pepe2012')
print(f"  Usuario: {user.username}")
print(f"  Proveedor: {user.llm_provider}")
print(f"  API Key: {user.llm_api_key[:20]}...")

if user.llm_provider != 'nvidia':
    print(f"  [WARNING] Usuario usa '{user.llm_provider}', cambiando a 'nvidia'...")
    user.llm_provider = 'nvidia'
    user.save()

# FASE 1: Limpiar ChromaDB anterior
print("\n[FASE 1] Limpiando ChromaDB anterior...")
from agent_ia_core import config
chroma_path = Path(config.CHROMA_PERSIST_DIRECTORY)
if chroma_path.exists():
    try:
        shutil.rmtree(chroma_path)
        print(f"  [OK] ChromaDB eliminado: {chroma_path}")
    except Exception as e:
        print(f"  [ERROR] No se pudo eliminar: {e}")
else:
    print(f"  [INFO] No existe ChromaDB previo en: {chroma_path}")

# FASE 2: Verificar licitaciones disponibles
print("\n[FASE 2] Verificando licitaciones en BD...")
tenders = Tender.objects.exclude(xml_content='').exclude(xml_content__isnull=True)
print(f"  Licitaciones con XML: {tenders.count()}")
if tenders.count() == 0:
    print("  [ERROR] No hay licitaciones para indexar!")
    sys.exit(1)

for tender in tenders[:5]:
    print(f"    - {tender.ojs_notice_id}: {len(tender.xml_content)} chars")

# FASE 3: Indexar con NVIDIA
print("\n[FASE 3] Indexando licitaciones con NVIDIA...")
vectorization_service = VectorizationService(user=user)

def progress_callback(data):
    msg_type = data.get('type', '')
    if msg_type == 'start':
        print(f"  Iniciando: {data.get('total', 0)} licitaciones")
    elif msg_type == 'progress':
        tender_id = data.get('tender_id', '')
        print(f"  [{data.get('current', 0)}/{data.get('total', 0)}] {tender_id}")
    elif msg_type == 'error':
        print(f"  [ERROR] {data.get('tender_id', '')}: {data.get('error', '')}")

result = vectorization_service.index_all_tenders(progress_callback=progress_callback)

print(f"\n  Resultado:")
print(f"    Success: {result.get('success', False)}")
print(f"    Indexed: {result.get('indexed_count', 0)}")
print(f"    Chunks: {result.get('total_chunks', 0)}")
print(f"    Errors: {result.get('error_count', 0)}")

if not result.get('success') or result.get('total_chunks', 0) == 0:
    print("  [ERROR] Indexación falló!")
    sys.exit(1)

# FASE 4: Verificar ChromaDB
print("\n[FASE 4] Verificando ChromaDB...")
try:
    import chromadb
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_collection(name=config.CHROMA_COLLECTION_NAME)
    count = collection.count()
    print(f"  ChromaDB Collection: {config.CHROMA_COLLECTION_NAME}")
    print(f"  Chunks en ChromaDB: {count}")

    if count == 0:
        print("  [ERROR] ChromaDB está vacío!")
        sys.exit(1)
except Exception as e:
    print(f"  [ERROR] No se pudo verificar ChromaDB: {e}")
    sys.exit(1)

# FASE 5: Probar Chat con RAG
print("\n[FASE 5] Probando Chat RAG con NVIDIA...")
chat_service = ChatAgentService(user=user)

questions = [
    "¿Cuántas licitaciones hay disponibles?",
    "¿Qué licitaciones están relacionadas con software?",
]

for i, question in enumerate(questions, 1):
    print(f"\n[Q{i}] {question}")
    try:
        response = chat_service.process_message(question)
        print(f"[A{i}] {response['content'][:250]}...")
        print(f"  Ruta: {response['metadata'].get('route', 'unknown')}")
        print(f"  Docs: {response['metadata'].get('num_documents', 0)}")

        if response['metadata'].get('num_documents', 0) == 0:
            print(f"  [WARNING] No se recuperaron documentos!")
    except Exception as e:
        print(f"[ERROR] {str(e)[:150]}")
        import traceback
        traceback.print_exc()

# FINAL
print("\n" + "="*70)
print("TEST COMPLETADO")
print("="*70)
print(f"\nResumen:")
print(f"  Proveedor: NVIDIA NIM")
print(f"  Licitaciones indexadas: {result.get('indexed_count', 0)}")
print(f"  Chunks totales: {result.get('total_chunks', 0)}")
print(f"  ChromaDB Path: {chroma_path}")
print(f"  Collection: {config.CHROMA_COLLECTION_NAME}")
