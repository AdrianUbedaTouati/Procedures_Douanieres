# -*- coding: utf-8 -*-
"""
Configuración del Chatbot Base.

Este archivo contiene la configuración específica del agente base con function calling.
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# ================================================
# CONFIGURACIÓN DEL AGENTE BASE
# ================================================

CHATBOT_CONFIG = {
    'name': 'Base Agent',
    'description': 'Agente genérico con function calling para web search y navegación',

    # Parámetros del agente
    'max_iterations': 5,
    'temperature': 0.3,

    # Tools habilitadas por defecto
    'tools_enabled': ['web_search', 'browse_webpage'],

    # Timeout para llamadas al LLM (segundos)
    'llm_timeout': 120,

    # Número máximo de reintentos por tool
    'max_tool_retries': 3,
}

# ================================================
# CONFIGURACIÓN DE MODELOS POR PROVEEDOR
# ================================================

MODEL_CONFIG = {
    'ollama': {
        'default_model': 'qwen2.5:7b',
        'base_url': 'http://localhost:11434',
    },
    'openai': {
        'default_model': 'gpt-4o-mini',
    },
    'google': {
        'default_model': 'gemini-2.5-flash',
    },
}

# ================================================
# CONFIGURACIÓN DE LOGGING
# ================================================

LOG_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
}
