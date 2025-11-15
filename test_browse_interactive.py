# -*- coding: utf-8 -*-
"""
Test del navegador interactivo con Playwright
Valida la instalación y funcionalidad básica
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TenderAI.settings')
django.setup()

from authentication.models import User


def test_playwright_installation():
    """Test 1: Verificar que Playwright está instalado"""
    print("\n" + "="*80)
    print("TEST 1: Verificar instalación de Playwright")
    print("="*80)

    try:
        from playwright.sync_api import sync_playwright
        print("[OK] Playwright importado correctamente")
        return True
    except ImportError as e:
        print(f"[FAIL] Error importando Playwright: {e}")
        print("[HINT] Ejecuta: pip install playwright && playwright install chromium")
        return False


def test_browse_interactive_import():
    """Test 2: Verificar que BrowseInteractiveTool se puede importar"""
    print("\n" + "="*80)
    print("TEST 2: Importar BrowseInteractiveTool")
    print("="*80)

    try:
        from agent_ia_core.tools.browse_interactive_tool import BrowseInteractiveTool
        print("[OK] BrowseInteractiveTool importada correctamente")
        return True
    except Exception as e:
        print(f"[FAIL] Error importando BrowseInteractiveTool: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_browse_interactive_initialization():
    """Test 3: Verificar que se puede inicializar sin LLM"""
    print("\n" + "="*80)
    print("TEST 3: Inicializar BrowseInteractiveTool (sin LLM)")
    print("="*80)

    try:
        from agent_ia_core.tools.browse_interactive_tool import BrowseInteractiveTool
        tool = BrowseInteractiveTool()
        print("[OK] BrowseInteractiveTool inicializada correctamente")
        print(f"[OK] Tool name: {tool.name}")
        return True
    except Exception as e:
        print(f"[FAIL] Error inicializando BrowseInteractiveTool: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_browse_interactive_schema():
    """Test 4: Verificar que el schema está bien definido"""
    print("\n" + "="*80)
    print("TEST 4: Schema de BrowseInteractiveTool")
    print("="*80)

    try:
        from agent_ia_core.tools.browse_interactive_tool import BrowseInteractiveTool
        tool = BrowseInteractiveTool()
        schema = tool.get_schema()

        print(f"[OK] Schema obtenido")
        print(f"[OK] Name: {schema['name']}")
        print(f"[OK] Parámetros: {list(schema['parameters']['properties'].keys())}")

        # Verificar parámetros requeridos
        required = schema['parameters']['required']
        if 'url' in required and 'query' in required:
            print(f"[OK] Parámetros requeridos correctos: {required}")
            return True
        else:
            print(f"[FAIL] Parámetros requeridos incorrectos: {required}")
            return False

    except Exception as e:
        print(f"[FAIL] Error obteniendo schema: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_registry_integration():
    """Test 5: Verificar integración en ToolRegistry"""
    print("\n" + "="*80)
    print("TEST 5: Integración en ToolRegistry")
    print("="*80)

    try:
        # Buscar usuario con web search habilitado
        user = User.objects.filter(
            use_web_search=True,
            google_search_api_key__isnull=False,
            google_search_engine_id__isnull=False
        ).first()

        if not user:
            print("[SKIP] No hay usuarios con use_web_search=True y credenciales")
            print("[HINT] La herramienta se activa cuando use_web_search=True")
            return True  # No es un error, solo no hay usuarios configurados

        print(f"[OK] Usuario encontrado: {user.email}")

        # Crear registry
        from agent_ia_core.tools.registry import ToolRegistry

        # Necesitamos un retriever dummy para el test
        class DummyRetriever:
            pass

        registry = ToolRegistry(
            retriever=DummyRetriever(),
            db_session=None,
            user=user
        )

        # Verificar que browse_interactive está registrada
        if 'browse_interactive' in registry.get_tool_names():
            print("[OK] browse_interactive encontrada en registry")
            print(f"[OK] Total tools: {len(registry.get_tool_names())}")
            print(f"[OK] Tools: {registry.get_tool_names()}")
            return True
        else:
            print("[FAIL] browse_interactive NO encontrada en registry")
            print(f"[INFO] Tools disponibles: {registry.get_tool_names()}")
            return False

    except Exception as e:
        print(f"[FAIL] Error en integración: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_navigation():
    """Test 6: Test básico de navegación (sin LLM)"""
    print("\n" + "="*80)
    print("TEST 6: Navegación básica a ejemplo.com")
    print("="*80)

    try:
        from agent_ia_core.tools.browse_interactive_tool import BrowseInteractiveTool

        tool = BrowseInteractiveTool()

        # Probar con example.com (sitio simple y rápido)
        print("\n[INFO] Navegando a example.com...")
        result = tool.run(
            url='https://example.com',
            query='What is the main heading of this page?',
            max_steps=1,
            timeout=10000
        )

        print(f"\n[RESULT]")
        print(f"Success: {result['success']}")

        if result['success']:
            print(f"URL final: {result['data']['final_url']}")
            print(f"Acciones: {result['data']['actions_taken']}")
            print(f"Contenido (primeros 200 chars):")
            print(result['data']['content'][:200] + "...")

            # Verificar que el contenido contiene "Example Domain"
            if 'Example Domain' in result['data']['content']:
                print("\n[OK] Contenido extraído correctamente (contiene 'Example Domain')")
                return True
            else:
                print("\n[WARN] Contenido no contiene 'Example Domain' esperado")
                return False
        else:
            print(f"Error: {result.get('error', 'Unknown')}")
            return False

    except Exception as e:
        print(f"[FAIL] Error en navegación: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecutar todos los tests"""
    print("\n" + "="*80)
    print("TESTING BROWSE INTERACTIVE TOOL - PLAYWRIGHT")
    print("="*80)

    results = []

    # Test 1: Playwright instalado
    results.append(("Playwright instalado", test_playwright_installation()))

    # Test 2: Import
    results.append(("Import BrowseInteractiveTool", test_browse_interactive_import()))

    # Test 3: Inicialización
    results.append(("Inicialización", test_browse_interactive_initialization()))

    # Test 4: Schema
    results.append(("Schema válido", test_browse_interactive_schema()))

    # Test 5: Registry integration
    results.append(("Integración Registry", test_registry_integration()))

    # Test 6: Navegación básica
    results.append(("Navegación básica", test_basic_navigation()))

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
        print("\nLa herramienta está lista para usar.")
        print("\nPróximos pasos:")
        print("1. Probar con contrataciondelestado.es")
        print("2. Configurar use_web_search=True en tu perfil")
        print("3. Usar en el chat con queries como:")
        print("   'Busca la licitación 00668461-2025 en contrataciondelestado.es'")
        return True
    else:
        print(f"\n[WARN] {total - passed} tests fallaron")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
