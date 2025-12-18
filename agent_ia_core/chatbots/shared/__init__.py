# -*- coding: utf-8 -*-
"""
Shared - Infraestructura compartida entre chatbots.

Este módulo contiene los componentes fundamentales del sistema de tools:
- ToolDefinition: Dataclass para definir tools
- ToolRegistry: Registro con autodiscovery y dependency injection
"""

from .base import ToolDefinition
from .registry import ToolRegistry

__all__ = ['ToolDefinition', 'ToolRegistry']
