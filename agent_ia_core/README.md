# Agent IA Core

Motor de agentes inteligentes con Function Calling para el sistema de procedimientos aduaneros.

## Estructura

```
agent_ia_core/
├── __init__.py                 # Re-export de FunctionCallingAgent
└── chatbots/
    ├── __init__.py
    ├── shared/                 # Infraestructura compartida
    │   ├── base.py             # ToolDefinition (dataclass)
    │   └── registry.py         # ToolRegistry (gestión de tools)
    │
    ├── base/                   # Chatbot Base (genérico)
    │   ├── agent.py            # FunctionCallingAgent
    │   ├── config.py           # Configuración
    │   ├── prompts.py          # System prompts
    │   └── tools/
    │       ├── web_search.py
    │       └── browse_webpage.py
    │
    └── etapes_classification_taric/  # Chatbot Classification TARIC
        ├── config.py           # Configuración específica
        ├── prompts.py          # Prompts de classification
        ├── service.py          # TARICClassificationService
        └── tools/
            ├── get_expedition_documents.py
            └── search_taric_database.py
```

## Filosofía

**Cada chatbot es completamente independiente** con su propio:
- `config.py` - Configuración específica
- `prompts.py` - System prompts y templates
- `tools/` - Herramientas especializadas

Solo se comparte la infraestructura básica en `shared/`:
- `ToolDefinition` - Definición de herramientas
- `ToolRegistry` - Registro y ejecución de tools

## Uso

### Importar el agente base

```python
from agent_ia_core import FunctionCallingAgent

agent = FunctionCallingAgent(
    llm_provider='google',  # 'ollama', 'openai', 'google'
    llm_model='gemini-2.5-flash',
    llm_api_key='your-api-key',
    user=request.user
)

response = agent.query("¿Qué tiempo hace en Madrid?")
```

### Usar un chatbot especializado

```python
from agent_ia_core.chatbots.etapes_classification_taric.service import TARICClassificationService

service = TARICClassificationService(expedition=expedition, user=request.user)
welcome = service.get_welcome_message()
response = service.process_message("Tengo un ordenador portátil para clasificar")
```

### Crear un nuevo chatbot

1. Crear carpeta en `chatbots/`:
```
chatbots/
└── mi_nuevo_chatbot/
    ├── __init__.py
    ├── config.py
    ├── prompts.py
    ├── service.py
    └── tools/
        ├── __init__.py
        └── mi_tool.py
```

2. Definir configuración en `config.py`:
```python
CHATBOT_CONFIG = {
    'name': 'Mi Chatbot',
    'max_iterations': 10,
    'temperature': 0.3,
    'tools_enabled': ['mi_tool'],
}
```

3. Crear prompts en `prompts.py`:
```python
SYSTEM_PROMPT = """Tu eres un asistente especializado en..."""
WELCOME_MESSAGE = """Bienvenido! Puedo ayudarte con..."""
```

4. Definir tools en `tools/mi_tool.py`:
```python
from agent_ia_core.chatbots.shared import ToolDefinition

def mi_funcion(param1: str, param2: int = 5) -> dict:
    return {'success': True, 'data': {...}}

TOOL_DEFINITION = ToolDefinition(
    name='mi_tool',
    description='Descripción para el LLM',
    parameters={
        'type': 'object',
        'properties': {
            'param1': {'type': 'string', 'description': '...'},
            'param2': {'type': 'integer', 'description': '...'}
        },
        'required': ['param1']
    },
    function=mi_funcion,
    category='mi_categoria'
)
```

5. Autodiscovery en `tools/__init__.py`:
```python
from agent_ia_core.chatbots.shared import ToolDefinition
import importlib
from pathlib import Path

ALL_TOOLS = []

for file_path in Path(__file__).parent.glob("*.py"):
    if file_path.name == "__init__.py":
        continue
    module = importlib.import_module(f".{file_path.stem}", package=__package__)
    if hasattr(module, "TOOL_DEFINITION"):
        tool_def = module.TOOL_DEFINITION
        if isinstance(tool_def, dict):
            tool_def = ToolDefinition(**tool_def)
        ALL_TOOLS.append(tool_def)
```

## Proveedores LLM soportados

| Proveedor | Modelos | Function Calling |
|-----------|---------|------------------|
| Ollama | qwen2.5:7b, llama3.2, etc. | ✓ Nativo |
| OpenAI | gpt-4o, gpt-4o-mini | ✓ Nativo |
| Google | gemini-2.5-flash, gemini-2.5-pro | ✓ Nativo |

## ToolDefinition

Cada tool se define con:

```python
@dataclass
class ToolDefinition:
    name: str           # Nombre único (debe coincidir con archivo .py)
    description: str    # Descripción para el LLM
    parameters: dict    # JSON Schema de parámetros
    function: Callable  # Función Python a ejecutar
    category: str       # Categoría (web, classification, etc.)
```

Métodos disponibles:
- `to_openai_format()` - Formato OpenAI/Ollama
- `to_gemini_format()` - Formato Google Gemini
- `get_reviewer_format()` - Formato texto para prompts

## ToolRegistry

El registry gestiona:
- Autodiscovery de tools
- Inyección de dependencias (user, llm, api_keys, etc.)
- Ejecución con reintentos
- Conversión de formatos por proveedor

```python
from agent_ia_core.chatbots.shared import ToolRegistry
from agent_ia_core.chatbots.base.tools import ALL_TOOLS

registry = ToolRegistry(
    all_tools=ALL_TOOLS,
    user=request.user,
    llm=llm_instance,
    google_api_key='...',
    google_engine_id='...'
)

# Ejecutar tool
result = registry.execute_tool('web_search', query='precio bitcoin')

# Obtener tools para LLM
tools = registry.get_openai_tools()
```
