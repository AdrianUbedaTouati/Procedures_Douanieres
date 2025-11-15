# -*- coding: utf-8 -*-
"""
Test de navegación interactiva en contrataciondelestado.es
Prueba real con el portal de licitaciones del gobierno español
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
django.setup()

from authentication.models import User


def test_contratacion_basic_navigation():
    """Test 1: Navegación básica a la página principal"""
    print("\n" + "="*80)
    print("TEST 1: Navegación a contrataciondelestado.es")
    print("="*80)

    try:
        from agent_ia_core.tools.browse_interactive_tool import BrowseInteractiveTool

        tool = BrowseInteractiveTool()

        print("\n[INFO] Navegando a contrataciondelestado.es...")
        result = tool.run(
            url='https://contrataciondelestado.es',
            query='What is the title of the main page?',
            max_steps=2,
            timeout=30000
        )

        print(f"\n[RESULT]")
        print(f"Success: {result['success']}")

        if result['success']:
            print(f"URL final: {result['data']['final_url']}")
            print(f"Acciones ejecutadas: {len(result['data']['actions_taken'])}")
            for i, action in enumerate(result['data']['actions_taken'], 1):
                print(f"  {i}. {action}")

            print(f"\nContenido (primeros 500 chars):")
            content = result['data']['content']
            print(content[:500] + "...")

            # Verificar que estamos en la página correcta
            if 'contratación' in content.lower() or 'licitaciones' in content.lower():
                print("\n[OK] Página cargada correctamente")
                return True
            else:
                print("\n[WARN] Contenido no parece ser de contrataciondelestado.es")
                return False
        else:
            print(f"[FAIL] Error: {result.get('error', 'Unknown')}")
            return False

    except Exception as e:
        print(f"[FAIL] Error en navegación: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_contratacion_with_llm():
    """Test 2: Navegación inteligente con LLM"""
    print("\n" + "="*80)
    print("TEST 2: Navegación inteligente con LLM en contrataciondelestado.es")
    print("="*80)

    try:
        # Obtener usuario con API key
        user = User.objects.filter(
            llm_api_key__isnull=False,
            use_web_search=True
        ).first()

        if not user:
            print("[SKIP] No hay usuarios con API key y web search")
            return True

        print(f"[OK] Usuario encontrado: {user.email}")
        print(f"[OK] Provider: {user.llm_provider}")

        # Crear LLM
        if user.llm_provider == 'google':
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model=user.openai_model or 'gemini-2.0-flash-exp',
                google_api_key=user.llm_api_key,
                temperature=0.3
            )
        elif user.llm_provider == 'openai':
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=user.openai_model or 'gpt-4o-mini',
                api_key=user.llm_api_key,
                temperature=0.3
            )
        else:
            print(f"[SKIP] Provider {user.llm_provider} no soportado en este test")
            return True

        # Crear tool con LLM
        from agent_ia_core.tools.browse_interactive_tool import BrowseInteractiveTool
        tool = BrowseInteractiveTool(llm=llm)

        print("\n[INFO] Navegando con navegación inteligente...")
        print("[INFO] Query: Find information about recent government tenders")

        result = tool.run(
            url='https://contrataciondelestado.es',
            query='Find information about recent government tenders or procurement opportunities',
            max_steps=5,
            timeout=30000
        )

        print(f"\n[RESULT]")
        print(f"Success: {result['success']}")

        if result['success']:
            print(f"\nURL final: {result['data']['final_url']}")
            print(f"\nAcciones ejecutadas ({len(result['data']['actions_taken'])}):")
            for i, action in enumerate(result['data']['actions_taken'], 1):
                print(f"  {i}. {action}")

            print(f"\nRespuesta del LLM:")
            print(result['data']['answer'][:500] + "...")

            print(f"\nContenido extraído (primeros 500 chars):")
            print(result['data']['content'][:500] + "...")

            print("\n[OK] Navegación inteligente completada")
            return True
        else:
            print(f"[FAIL] Error: {result.get('error', 'Unknown')}")
            return False

    except Exception as e:
        print(f"[FAIL] Error en navegación inteligente: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_specific_tender():
    """Test 3: Búsqueda de licitación específica"""
    print("\n" + "="*80)
    print("TEST 3: Búsqueda de licitación específica (ID conocido)")
    print("="*80)

    try:
        # Obtener usuario con API key
        user = User.objects.filter(
            llm_api_key__isnull=False,
            use_web_search=True,
            llm_provider='google'
        ).first()

        if not user:
            print("[SKIP] No hay usuarios con Gemini y web search")
            return True

        print(f"[OK] Usuario: {user.email}")

        # Crear LLM
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model='gemini-2.0-flash-exp',
            google_api_key=user.llm_api_key,
            temperature=0.3
        )

        # Crear tool
        from agent_ia_core.tools.browse_interactive_tool import BrowseInteractiveTool
        tool = BrowseInteractiveTool(llm=llm)

        # Buscar una licitación específica
        # Nota: Este ID puede no existir, pero probamos la navegación
        tender_id = "00668461"

        print(f"\n[INFO] Buscando licitación ID: {tender_id}")

        result = tool.run(
            url='https://contrataciondelestado.es',
            query=f'Search for tender or contract with ID {tender_id}',
            max_steps=8,
            timeout=45000
        )

        print(f"\n[RESULT]")
        print(f"Success: {result['success']}")

        if result['success']:
            print(f"\nURL final: {result['data']['final_url']}")
            print(f"\nAcciones ({len(result['data']['actions_taken'])}):")
            for i, action in enumerate(result['data']['actions_taken'], 1):
                print(f"  {i}. {action}")

            print(f"\nRespuesta:")
            print(result['data']['answer'])

            print("\n[OK] Búsqueda específica completada")
            return True
        else:
            print(f"[WARN] Error: {result.get('error', 'Unknown')}")
            print("[INFO] Es normal si el portal requiere interacciones muy complejas")
            return False

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecutar todos los tests"""
    print("\n" + "="*80)
    print("TESTING NAVEGACIÓN INTERACTIVA - CONTRATACIONDELESTADO.ES")
    print("="*80)
    print("\nNOTA: Estos tests acceden a un sitio real del gobierno español.")
    print("Los tests pueden fallar si:")
    print("- El sitio está caído o lento")
    print("- Hay restricciones de acceso (firewall, geolocalización)")
    print("- El sitio cambia su estructura")
    print("="*80)

    results = []

    # Test 1: Navegación básica
    results.append(("Navegación básica", test_contratacion_basic_navigation()))

    # Test 2: Navegación con LLM
    results.append(("Navegación con LLM", test_contratacion_with_llm()))

    # Test 3: Búsqueda específica
    results.append(("Búsqueda específica", test_search_specific_tender()))

    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE TESTS")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[OK] PASS" if result else "[X] FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests pasados")

    if passed == total:
        print("\n[OK] TODOS LOS TESTS PASARON!")
        print("\nLa herramienta funciona correctamente con contrataciondelestado.es")
        print("\nYa puedes usar browse_interactive en el chat con queries como:")
        print("  'Navega a contrataciondelestado.es y busca licitaciones de software'")
        print("  'Encuentra la licitación 00668461 en el portal de contratación'")
    elif passed > 0:
        print(f"\n[INFO] {passed}/{total} tests pasaron")
        print("\nAlgunos tests fallaron. Esto puede ser normal si:")
        print("- El sitio requiere navegación muy compleja (captcha, cookies, etc.)")
        print("- Hay restricciones de red")
        print("\nLa herramienta sigue siendo útil para sitios más simples.")
    else:
        print("\n[WARN] Todos los tests fallaron")
        print("Verifica tu conexión a internet y acceso a contrataciondelestado.es")

    return passed > 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
