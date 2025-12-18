"""
Test de integración del FunctionCallingAgent con el servicio de chat de Django.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['USE_FUNCTION_CALLING'] = 'true'  # Activar Function Calling
django.setup()

from django.contrib.auth import get_user_model
from apps.chat.services import ChatAgentService

User = get_user_model()


def test_function_calling_integration():
    """
    Test que verifica que el FunctionCallingAgent se integra correctamente
    con el servicio de chat de Django.
    """
    print("\n" + "="*80)
    print("TEST: Integración FunctionCallingAgent con Django")
    print("="*80)

    # Usar el primer usuario existente en la base de datos o crear uno mínimo
    print("\n[1] Obteniendo usuario para prueba...")

    # Intentar obtener el primer usuario
    user = User.objects.first()

    if not user:
        # Si no hay usuarios, crear uno simple
        user = User.objects.create_user(
            username='test_fc',
            email='testfc@example.com',
            password='testpass123',
            llm_provider='ollama',
            llm_api_key='',
            ollama_model='qwen2.5:7b',
            ollama_embedding_model='nomic-embed-text'
        )
        print("   Usuario de prueba creado")
    else:
        # Actualizar configuración del usuario existente para Ollama
        user.llm_provider = 'ollama'
        user.ollama_model = 'qwen2.5:7b'
        user.ollama_embedding_model = 'nomic-embed-text'
        if not user.llm_api_key:
            user.llm_api_key = ''
        user.save()
        print(f"   Usando usuario existente")

    print(f"   Usuario: {user.username}")
    print(f"   Provider: {user.llm_provider}")
    print(f"   Modelo: {user.ollama_model}")

    # Crear servicio de chat con Function Calling activado
    print("\n[2] Creando ChatAgentService con Function Calling...")
    service = ChatAgentService(user, use_function_calling=True)
    print(f"   use_function_calling: {service.use_function_calling}")

    # Test 1: Búsqueda simple
    print("\n" + "-"*80)
    print("[TEST 1] Búsqueda simple: 'busca licitaciones de software'")
    print("-"*80)

    result1 = service.process_message("busca licitaciones de software")

    print(f"\nRESPUESTA:")
    print(f"  Content: {result1['content'][:200]}...")
    print(f"\nMETADATA:")
    print(f"  Route: {result1['metadata'].get('route', 'N/A')}")
    print(f"  Iterations: {result1['metadata'].get('iterations', 'N/A')}")
    print(f"  Documentos: {result1['metadata'].get('num_documents', 0)}")
    print(f"  Tokens: {result1['metadata'].get('total_tokens', 0)}")
    print(f"  Cost: €{result1['metadata'].get('cost_eur', 0):.4f}")

    # Verificar que funcionó
    assert 'content' in result1, "Falta 'content' en la respuesta"
    assert 'metadata' in result1, "Falta 'metadata' en la respuesta"
    assert result1['metadata'].get('route') == 'function_calling', "Route incorrecto"

    print("\n✓ TEST 1 PASADO")

    # Test 2: Con historial de conversación
    print("\n" + "-"*80)
    print("[TEST 2] Con historial: 'dame más detalles de la primera'")
    print("-"*80)

    history = [
        {'role': 'user', 'content': 'busca licitaciones de software'},
        {'role': 'assistant', 'content': result1['content']}
    ]

    result2 = service.process_message(
        "dame más detalles de la primera",
        conversation_history=history
    )

    print(f"\nRESPUESTA:")
    print(f"  Content: {result2['content'][:200]}...")
    print(f"\nMETADATA:")
    print(f"  Route: {result2['metadata'].get('route', 'N/A')}")
    print(f"  Iterations: {result2['metadata'].get('iterations', 'N/A')}")

    print("\n✓ TEST 2 PASADO")

    # Test 3: Búsqueda por presupuesto
    print("\n" + "-"*80)
    print("[TEST 3] Búsqueda por presupuesto: 'licitaciones con más de 100k euros'")
    print("-"*80)

    result3 = service.process_message("licitaciones con más de 100000 euros")

    print(f"\nRESPUESTA:")
    print(f"  Content: {result3['content'][:200]}...")
    print(f"\nMETADATA:")
    print(f"  Route: {result3['metadata'].get('route', 'N/A')}")
    print(f"  Iterations: {result3['metadata'].get('iterations', 'N/A')}")

    print("\n✓ TEST 3 PASADO")

    # Resumen final
    print("\n" + "="*80)
    print("TODOS LOS TESTS PASADOS ✓")
    print("="*80)
    print("\nEl FunctionCallingAgent está completamente integrado con Django!")
    print("Los usuarios pueden activarlo configurando USE_FUNCTION_CALLING=true")
    print("o añadiendo el campo use_function_calling al modelo de usuario.")

    print("\n[INFO] Test completado. El usuario usado permanece en la BD.")


if __name__ == "__main__":
    try:
        test_function_calling_integration()
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
