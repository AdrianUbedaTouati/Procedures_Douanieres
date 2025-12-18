# -*- coding: utf-8 -*-
"""
Agent IA Core - Motor del agente inteligente.

Estructura:
- chatbots/: Chatbots especializados (cada uno independiente)
  - shared/: Infraestructura compartida (ToolDefinition, ToolRegistry)
  - base/: Agente base con Function Calling
  - etapes_classification_taric/: Chatbot de clasificación TARIC

Cada chatbot contiene su propio:
- config.py
- prompts.py
- tools/
"""

# Re-export del agente base para uso directo
from .chatbots import FunctionCallingAgent

__all__ = ['FunctionCallingAgent']
