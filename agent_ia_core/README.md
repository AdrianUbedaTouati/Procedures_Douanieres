# Agent IA Core

Moteur d'agents intelligents avec Function Calling pour le systeme de procedures douanieres.

## Structure

```
agent_ia_core/
+-- __init__.py
+-- chatbots/
    +-- __init__.py
    +-- shared/                 # Infrastructure partagee
    |   +-- base.py             # ToolDefinition (dataclass)
    |   +-- registry.py         # ToolRegistry (gestion des tools)
    |
    +-- etapes_classification_taric/  # Chatbot Classification TARIC
        +-- config.py           # Configuration specifique
        +-- prompts.py          # Prompts de classification
        +-- service.py          # TARICClassificationService
        +-- tools/              # 4 outils du chatbot
            +-- web_search.py
            +-- browse_webpage.py
            +-- analyze_documents.py
            +-- fetch_pdf.py
```

## Philosophie

**Chaque chatbot est completement independant** avec son propre:
- config.py - Configuration specifique
- prompts.py - System prompts et templates
- tools/ - Outils specialises

Seule l'infrastructure basique est partagee dans shared/:
- ToolDefinition - Definition des outils
- ToolRegistry - Registre et execution des outils

## Les 4 Outils du Chatbot TARIC

| Outil | Description | Innovation |
|-------|-------------|------------|
| web_search | Recherche Google Custom Search API | Informations actualisees sur les codes TARIC |
| browse_webpage | Extraction de contenu web | Early stopping : economie de 92% des tokens |
| analyze_documents | Analyse Vision GPT-4o | Strategie intelligente PDF : texte vs image |
| fetch_pdf | Telechargement PDF | Sauvegarde automatique dans l'expedition |

## Utilisation

### Utiliser le service de classification

```python
from agent_ia_core.chatbots.etapes_classification_taric.service import TARICClassificationService

service = TARICClassificationService(user=request.user, expedition=expedition)

# Message de bienvenue
welcome = service.get_welcome_message()

# Traiter un message
response = service.process_message(
    message="J'ai un ordinateur portable a classifier",
    conversation_history=[]
)

# response contient:
# - content: texte de la reponse
# - metadata: {proposals: [...], tools_used: [...]}
```

### Creer un nouvel outil

1. Creer fichier dans tools/:

```python
# tools/mon_outil.py

from agent_ia_core.chatbots.shared import ToolDefinition

def mon_outil(param1: str, param2: int = 5, **kwargs) -> dict:
    """
    Execute l'outil avec les parametres donnes.
    **kwargs contient: user, llm, api_key, etc. (injectes par registry)
    """
    return {
        'success': True,
        'data': {...}
    }

TOOL_DEFINITION = ToolDefinition(
    name='mon_outil',
    description='Description pour le LLM',
    parameters={
        'type': 'object',
        'properties': {
            'param1': {'type': 'string', 'description': '...'},
            'param2': {'type': 'integer', 'description': '...', 'default': 5}
        },
        'required': ['param1']
    },
    function=mon_outil,
    category='ma_categorie'
)
```

2. L'outil sera autodecouvert au demarrage (via tools/__init__.py)

### Creer un nouveau chatbot

1. Creer dossier dans chatbots/:
```
chatbots/
+-- mon_chatbot/
    +-- __init__.py
    +-- config.py
    +-- prompts.py
    +-- service.py
    +-- tools/
        +-- __init__.py
        +-- mon_outil.py
```

2. Definir configuration dans config.py:
```python
CHATBOT_CONFIG = {
    'name': 'Mon Chatbot',
    'max_iterations': 10,
    'temperature': 0.3,
    'tools_enabled': ['mon_outil'],
}
```

3. Creer prompts dans prompts.py:
```python
SYSTEM_PROMPT = """Tu es un assistant specialise en..."""
WELCOME_MESSAGE = """Bienvenue! Je peux vous aider avec..."""
```

4. Implementer service.py avec la logique metier

## ToolDefinition

Chaque outil est defini avec:

```python
@dataclass
class ToolDefinition:
    name: str           # Nom unique
    description: str    # Description pour le LLM
    parameters: dict    # JSON Schema des parametres
    function: Callable  # Fonction Python a executer
    category: str       # Categorie (web, classification, etc.)
```

Methodes disponibles:
- to_openai_format() - Format OpenAI
- to_gemini_format() - Format Google Gemini
- get_reviewer_format() - Format texte pour prompts

## ToolRegistry

Le registry gere:
- Autodiscovery des outils
- Injection de dependances (user, llm, api_keys, etc.)
- Execution avec reintentos
- Conversion de formats par fournisseur

```python
from agent_ia_core.chatbots.shared import ToolRegistry
from agent_ia_core.chatbots.etapes_classification_taric.tools import ALL_TOOLS

registry = ToolRegistry(
    all_tools=ALL_TOOLS,
    user=request.user,
    llm=llm_instance,
    google_api_key='...',
    google_engine_id='...'
)

# Executer un outil
result = registry.execute_tool('web_search', query='code TARIC verre cristal')

# Obtenir les outils au format OpenAI
tools = registry.get_openai_tools()
```

## Extraction Structuree

Le service utilise OpenAI Structured Output pour extraire les codes TARIC:

```python
TARIC_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "proposals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code_taric": {"type": "string"},
                    "description": {"type": "string"},
                    "probability": {"type": "integer"},
                    "droits_douane": {"type": "string"},
                    "tva": {"type": "string"},
                    "justification": {"type": "string"}
                },
                "required": ["code_taric", "description", "probability"],
                "additionalProperties": False
            }
        }
    },
    "required": ["proposals"],
    "additionalProperties": False
}
```

Cela garantit un JSON valide a 100% avec les champs requis.

---

**Version:** 2.0.0
**Date:** Janvier 2026
