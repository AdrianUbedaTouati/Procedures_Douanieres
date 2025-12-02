# -*- coding: utf-8 -*-
"""
Tools Base - Infraestructura del sistema de herramientas.

Este paquete contiene los componentes fundamentales del sistema de tools:
- base.py: ToolDefinition dataclass
- registry.py: ToolRegistry con autodiscovery y dependency injection
- schema_converters.py: Utilidades de conversión de schemas
"""

from .base import ToolDefinition
from .registry import ToolRegistry

__all__ = ['ToolDefinition', 'ToolRegistry']
