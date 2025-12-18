"""
Prueba de concepto: Function Calling con Ollama
Demuestra cómo funcionaría el sistema nuevo con tools.
"""

import ollama
import json

# ============================================================================
# DEFINICIÓN DE TOOLS (simplificadas para la prueba)
# ============================================================================

TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'search_tenders',
            'description': 'Busca licitaciones usando palabras clave o temas. Usa esta función cuando el usuario quiera encontrar licitaciones sobre un tema específico, por ejemplo "software", "construcción", "Madrid", etc. Devuelve las licitaciones más relevantes.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'La búsqueda que el usuario quiere hacer. Ejemplo: "software", "desarrollo web", "construcción en Madrid"'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Cuántas licitaciones quieres que devuelva. Por defecto 6.',
                        'default': 6
                    }
                },
                'required': ['query']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'find_by_budget',
            'description': 'Busca licitaciones por cantidad de dinero. Úsala cuando el usuario pregunte por licitaciones caras, baratas, o dentro de un rango de presupuesto específico.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'min_euros': {
                        'type': 'number',
                        'description': 'Presupuesto mínimo en euros. Si el usuario dice "más de 100k", pon 100000 aquí',
                        'default': 0
                    },
                    'max_euros': {
                        'type': 'number',
                        'description': 'Presupuesto máximo en euros. Si el usuario dice "menos de 500k", pon 500000 aquí',
                        'default': 99999999
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Cuántos resultados devolver',
                        'default': 10
                    }
                }
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_tender_details',
            'description': 'Obtiene toda la información de una licitación específica cuando sabes su ID. Usa esta función cuando el usuario pregunte por una licitación concreta o cuando necesites más detalles de una licitación que encontraste con search_tenders.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'tender_id': {
                        'type': 'string',
                        'description': 'El ID de la licitación. Ejemplo: "00668461-2025"'
                    }
                },
                'required': ['tender_id']
            }
        }
    }
]

# ============================================================================
# SIMULACIÓN DE EJECUCIÓN DE TOOLS (mock functions)
# ============================================================================

def execute_search_tenders(query: str, limit: int = 6):
    """Simula búsqueda de licitaciones."""
    # Datos mock
    mock_results = [
        {
            'id': '00668461-2025',
            'title': 'Servicios de implementación SAP',
            'buyer': 'Fundación Estatal',
            'budget': 961200.0,
            'deadline': '2025-10-15'
        },
        {
            'id': '00677736-2025',
            'title': 'Software de gestión portuaria',
            'buyer': 'Autoridad Portuaria Las Palmas',
            'budget': 750000.0,
            'deadline': '2025-11-20'
        },
        {
            'id': '00670256-2025',
            'title': 'Contrato mixto SAP y licencias',
            'buyer': 'Ajuntament de València',
            'budget': 500000.0,
            'deadline': '2025-10-30'
        }
    ]

    return {
        'success': True,
        'count': len(mock_results[:limit]),
        'results': mock_results[:limit],
        'message': f'Encontradas {len(mock_results[:limit])} licitaciones para "{query}"'
    }

def execute_find_by_budget(min_euros: float = 0, max_euros: float = 99999999, limit: int = 10):
    """Simula búsqueda por presupuesto."""
    mock_results = [
        {
            'id': '00668461-2025',
            'title': 'Servicios SAP',
            'budget': 961200.0,
            'buyer': 'Fundación Estatal'
        },
        {
            'id': '00677736-2025',
            'title': 'Software portuario',
            'budget': 750000.0,
            'buyer': 'Autoridad Portuaria'
        }
    ]

    # Filtrar por rango
    filtered = [r for r in mock_results if min_euros <= r['budget'] <= max_euros]

    return {
        'success': True,
        'count': len(filtered[:limit]),
        'results': filtered[:limit],
        'message': f'Encontradas {len(filtered[:limit])} licitaciones entre {min_euros}€ y {max_euros}€'
    }

def execute_get_tender_details(tender_id: str):
    """Simula obtención de detalles."""
    mock_data = {
        '00668461-2025': {
            'id': '00668461-2025',
            'title': 'Servicios de implementación y mantenimiento SAP',
            'description': 'Servicios profesionales para implementación de sistema SAP ERP incluyendo módulos financieros, logística y recursos humanos.',
            'buyer_name': 'Fundación Estatal para la Formación en el Empleo',
            'buyer_type': 'Fundación pública',
            'budget_eur': 961200.0,
            'currency': 'EUR',
            'deadline': '2025-10-15T14:00:00',
            'publication_date': '2025-09-15',
            'contract_type': 'services',
            'procedure_type': 'open',
            'cpv_codes': ['72267100', '72000000'],
            'nuts_regions': ['ES', 'ES30'],
            'contact_email': 'licitaciones@fundae.es',
            'contact_phone': '+34 91 123 4567',
            'contact_url': 'https://fundae.es/licitaciones'
        }
    }

    if tender_id in mock_data:
        return {
            'success': True,
            'tender': mock_data[tender_id]
        }
    else:
        return {
            'success': False,
            'error': f'Licitación {tender_id} no encontrada'
        }

# ============================================================================
# EJECUTOR DE TOOLS
# ============================================================================

def execute_tool(tool_name: str, arguments: dict):
    """Ejecuta una tool según su nombre."""
    print(f"\n🔧 [TOOL EXECUTION] {tool_name}")
    print(f"   Argumentos: {json.dumps(arguments, indent=2, ensure_ascii=False)}")

    if tool_name == 'search_tenders':
        result = execute_search_tenders(**arguments)
    elif tool_name == 'find_by_budget':
        result = execute_find_by_budget(**arguments)
    elif tool_name == 'get_tender_details':
        result = execute_get_tender_details(**arguments)
    else:
        result = {'success': False, 'error': f'Tool {tool_name} no implementada'}

    print(f"   Resultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result

# ============================================================================
# AGENTE CON FUNCTION CALLING
# ============================================================================

def run_agent_with_tools(user_query: str, max_iterations: int = 5):
    """
    Ejecuta el agente con function calling.
    """
    print("="*80)
    print(f"USER QUERY: {user_query}")
    print("="*80)

    messages = [
        {
            'role': 'user',
            'content': user_query
        }
    ]

    iteration = 0
    tools_used = []

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- ITERACIÓN {iteration} ---")

        # Llamar a Ollama con las tools
        print(f"\n🤖 [LLM CALL] Llamando a Ollama con {len(TOOLS)} tools disponibles...")

        try:
            response = ollama.chat(
                model='qwen2.5:7b',
                messages=messages,
                tools=TOOLS
            )
        except Exception as e:
            print(f"❌ [ERROR] {e}")
            return {
                'answer': f'Error al comunicar con Ollama: {e}',
                'tools_used': tools_used,
                'iterations': iteration
            }

        assistant_message = response['message']

        # ¿Hay tool calls?
        tool_calls = assistant_message.get('tool_calls', [])

        if not tool_calls:
            # No hay tool calls, tenemos la respuesta final
            final_answer = assistant_message.get('content', '')
            print(f"\n✅ [RESPUESTA FINAL]")
            print(f"{final_answer}")

            return {
                'answer': final_answer,
                'tools_used': tools_used,
                'iterations': iteration
            }

        # Hay tool calls, ejecutarlas
        print(f"\n🛠️  [TOOL CALLS] El LLM quiere usar {len(tool_calls)} tool(s):")

        # Añadir mensaje del asistente (con tool calls) al historial
        messages.append({
            'role': 'assistant',
            'content': assistant_message.get('content', ''),
            'tool_calls': tool_calls
        })

        # Ejecutar cada tool call
        for tool_call in tool_calls:
            function = tool_call['function']
            tool_name = function['name']
            arguments = function.get('arguments', {})

            # Ejecutar la tool
            result = execute_tool(tool_name, arguments)
            tools_used.append(tool_name)

            # Añadir resultado al historial
            messages.append({
                'role': 'tool',
                'content': json.dumps(result, ensure_ascii=False)
            })

    # Max iterations alcanzado
    print(f"\n⚠️  [MAX ITERATIONS] Se alcanzó el máximo de {max_iterations} iteraciones")
    return {
        'answer': 'Lo siento, no pude completar la tarea en el número de pasos permitidos.',
        'tools_used': tools_used,
        'iterations': iteration
    }

# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("TEST: Function Calling con Ollama")
    print("Modelo: qwen2.5:7b")
    print("Tools disponibles: search_tenders, find_by_budget, get_tender_details")
    print("="*80)

    # Test 1: Búsqueda simple
    print("\n\n" + "#"*80)
    print("# TEST 1: Búsqueda simple")
    print("#"*80)
    result1 = run_agent_with_tools("busca licitaciones de software")
    print(f"\n📊 RESUMEN:")
    print(f"   - Respuesta: {result1['answer'][:100]}...")
    print(f"   - Tools usadas: {result1['tools_used']}")
    print(f"   - Iteraciones: {result1['iterations']}")

    # Test 2: Búsqueda por presupuesto
    print("\n\n" + "#"*80)
    print("# TEST 2: Búsqueda por presupuesto")
    print("#"*80)
    result2 = run_agent_with_tools("dame la licitación con más dinero")
    print(f"\n📊 RESUMEN:")
    print(f"   - Respuesta: {result2['answer'][:100]}...")
    print(f"   - Tools usadas: {result2['tools_used']}")
    print(f"   - Iteraciones: {result2['iterations']}")

    # Test 3: Detalles específicos
    print("\n\n" + "#"*80)
    print("# TEST 3: Detalles de licitación específica")
    print("#"*80)
    result3 = run_agent_with_tools("dame todos los detalles de la licitación 00668461-2025")
    print(f"\n📊 RESUMEN:")
    print(f"   - Respuesta: {result3['answer'][:100]}...")
    print(f"   - Tools usadas: {result3['tools_used']}")
    print(f"   - Iteraciones: {result3['iterations']}")

    print("\n\n" + "="*80)
    print("TESTS COMPLETADOS")
    print("="*80)
