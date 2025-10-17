"""
Script de Prueba de Integracin Agent_IA
Verifica: VectorizationService, ChatAgentService, y flujo completo
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
django.setup()

from django.contrib.auth import get_user_model
from tenders.models import Tender
from tenders.vectorization_service import VectorizationService
from chat.services import ChatAgentService

User = get_user_model()

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_vectorization_service():
    """Test 1: Verificar VectorizationService"""
    print_section("TEST 1: VectorizationService")

    try:
        # Obtener usuario con API key
        user = User.objects.filter(llm_api_key__isnull=False).exclude(llm_api_key='').first()

        if not user:
            print("[FAIL] No se encontro usuario con API key configurada")
            print("  Por favor, configura tu API key en el perfil de usuario")
            return False

        print(f"[OK] Usuario encontrado: {user.email}")
        print(f"  API Key: {user.llm_api_key[:20]}...")

        # Crear servicio
        service = VectorizationService(user=user)
        print("[OK] VectorizationService creado")

        # Verificar estado del vectorstore
        status = service.get_vectorstore_status()
        print(f"\n[Estado del Vectorstore]")
        print(f"  - Inicializado: {status['is_initialized']}")
        print(f"  - Documentos: {status.get('num_documents', 0)}")
        print(f"  - Chunks: {status.get('num_chunks', 0)}")
        print(f"  - Coleccin: {status.get('collection_name', 'N/A')}")
        print(f"  - Directorio: {status.get('persist_directory', 'N/A')}")

        return True

    except Exception as e:
        print(f"[FAIL] Error en VectorizationService: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chat_service():
    """Test 2: Verificar ChatAgentService"""
    print_section("TEST 2: ChatAgentService")

    try:
        # Obtener usuario con API key
        user = User.objects.filter(llm_api_key__isnull=False).exclude(llm_api_key='').first()

        if not user:
            print("[FAIL] No se encontr usuario con API key configurada")
            return False

        print(f"[OK] Usuario encontrado: {user.email}")

        # Crear servicio
        service = ChatAgentService(user=user)
        print("[OK] ChatAgentService creado")

        # Verificar que el agente se puede inicializar
        try:
            agent = service._get_agent()
            print("[OK] EFormsRAGAgent inicializado correctamente")
            print(f"  - Tipo: {type(agent).__name__}")
            print(f"  - Mdulo: {type(agent).__module__}")

            # Verificar que tiene los mtodos necesarios
            if hasattr(agent, 'query'):
                print("[OK] Mtodo 'query' disponible")
            else:
                print("[FAIL] Mtodo 'query' NO disponible")
                return False

            return True

        except Exception as e:
            print(f"[FAIL] Error al inicializar agente: {e}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"[FAIL] Error en ChatAgentService: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tenders_data():
    """Test 3: Verificar datos de licitaciones"""
    print_section("TEST 3: Datos de Licitaciones")

    try:
        total_tenders = Tender.objects.count()
        tenders_with_xml = Tender.objects.exclude(xml_content='').exclude(xml_content__isnull=True).count()

        print(f"[Estadisticas de Licitaciones]")
        print(f"  - Total de licitaciones: {total_tenders}")
        print(f"  - Licitaciones con XML: {tenders_with_xml}")
        print(f"  - Licitaciones sin XML: {total_tenders - tenders_with_xml}")

        if tenders_with_xml > 0:
            print(f"\n[OK] Hay {tenders_with_xml} licitaciones disponibles para indexar")

            # Mostrar una muestra
            sample = Tender.objects.exclude(xml_content='').exclude(xml_content__isnull=True).first()
            if sample:
                print(f"\n[Muestra de licitacion]")
                print(f"  - ID: {sample.ojs_notice_id}")
                print(f"  - Ttulo: {sample.title[:80]}...")
                print(f"  - Tamao XML: {len(sample.xml_content)} caracteres")

            return True
        else:
            print("\n[WARNING]  No hay licitaciones con XML disponibles para indexar")
            print("  Primero descarga algunas licitaciones desde la seccin 'Obtener'")
            return False

    except Exception as e:
        print(f"[FAIL] Error al verificar datos: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_ia_modules():
    """Test 4: Verificar mdulos de Agent_IA"""
    print_section("TEST 4: Mdulos de Agent_IA")

    try:
        # Importar mdulos de agent_ia_core
        from agent_ia_core import agent_graph
        print("[OK] agent_ia_core.agent_graph importado")

        from agent_ia_core import config
        print("[OK] agent_ia_core.config importado")

        # Verificar que EFormsRAGAgent existe
        if hasattr(agent_graph, 'EFormsRAGAgent'):
            print("[OK] EFormsRAGAgent disponible")
        else:
            print("[FAIL] EFormsRAGAgent NO disponible")
            return False

        # Verificar archivos de parsing y chunking
        try:
            from agent_ia_core.eforms_parser import parse_eforms_xml
            print("[OK] parse_eforms_xml importado")
        except ImportError as e:
            print(f"[FAIL] Error importando parse_eforms_xml: {e}")
            return False

        try:
            from agent_ia_core.chunking import chunk_tender_xml
            print("[OK] chunk_tender_xml importado")
        except ImportError as e:
            print(f"[FAIL] Error importando chunk_tender_xml: {e}")
            return False

        print("\n[OK] Todos los mdulos de Agent_IA disponibles")
        return True

    except ImportError as e:
        print(f"[FAIL] Error importando mdulos de Agent_IA: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*60)
    print("  PRUEBA DE INTEGRACION AGENT_IA - TenderAI Platform")
    print("="*60)

    results = {
        "Agent_IA Modules": test_agent_ia_modules(),
        "Tenders Data": test_tenders_data(),
        "VectorizationService": test_vectorization_service(),
        "ChatAgentService": test_chat_service(),
    }

    # Resumen
    print_section("RESUMEN DE PRUEBAS")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    for test_name, result in results.items():
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status}  {test_name}")

    print(f"\n[STATS] Resultados: {passed}/{total} pruebas pasadas")

    if failed == 0:
        print("\n[SUCCESS] Todas las pruebas pasaron! El sistema est listo.")
        print("\nPrximos pasos:")
        print("  1. Accede a http://127.0.0.1:8001/licitaciones/vectorizacion/")
        print("  2. Haz clic en 'Indexar Todo' para vectorizar las licitaciones")
        print("  3. Ve a http://127.0.0.1:8001/chat/ para probar el chat con RAG")
    else:
        print(f"\n[WARNING]  {failed} prueba(s) fallaron. Revisa los errores arriba.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
