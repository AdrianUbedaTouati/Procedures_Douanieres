# -*- coding: utf-8 -*-
"""
Chatbots especializados del sistema.

Estructura:
- base/: Agente base con Function Calling (FunctionCallingAgent)
- etapes_classification_taric/: Chatbot de clasificación TARIC

Cada subcarpeta contiene un chatbot con su propia configuración, prompts y tools.
"""

# Re-export del agente base para uso directo
from .base import FunctionCallingAgent

__all__ = ['FunctionCallingAgent']
