# -*- coding: utf-8 -*-
"""
Agent IA Core - Motor del agente inteligente.

Estructura:
- prompts/: System prompts
- tools/: Tools del agente (web_search, browse_webpage)
- config/: Configuración
"""

from . import config

# Re-exports for backward compatibility
from .agent_function_calling import FunctionCallingAgent

__all__ = [
    'config',
    'FunctionCallingAgent',
]
