# -*- coding: utf-8 -*-
"""
Chatbot Base - Agente con Function Calling.

Estructura independiente:
- agent.py: FunctionCallingAgent
- config.py: Configuración del agente
- prompts.py: Prompts del sistema
- tools/: Tools específicas de este chatbot (web_search, browse_webpage)
"""

from .agent import FunctionCallingAgent
from .config import CHATBOT_CONFIG, MODEL_CONFIG
from .prompts import build_system_prompt, SYSTEM_PROMPT
from .tools import ALL_TOOLS

__all__ = [
    'FunctionCallingAgent',
    'CHATBOT_CONFIG',
    'MODEL_CONFIG',
    'build_system_prompt',
    'SYSTEM_PROMPT',
    'ALL_TOOLS',
]
