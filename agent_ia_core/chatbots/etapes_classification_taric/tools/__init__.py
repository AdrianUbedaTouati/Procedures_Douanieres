# -*- coding: utf-8 -*-
"""
Tools especializadas para el chatbot de clasificacion TARIC.

Autodiscovery de tools para este chatbot especializado.
"""

import os
import importlib
from pathlib import Path
from typing import List
from agent_ia_core.chatbots.shared import ToolDefinition
import logging

logger = logging.getLogger(__name__)

# Lista de todos los ToolDefinition autodescubiertos
ALL_TOOLS: List[ToolDefinition] = []


def autodiscover_tools() -> List[ToolDefinition]:
    """
    Descubre automáticamente todas las tools en la carpeta tools/.

    Soporta dos formatos de TOOL_DEFINITION:
    - ToolDefinition (nuevo formato)
    - Dict (formato legacy, se convierte a ToolDefinition)

    Returns:
        Lista de ToolDefinition encontradas
    """
    tools = []
    tools_dir = Path(__file__).parent

    logger.info("[TARIC TOOLS] Escaneando tools del chatbot TARIC...")

    # Obtener todos los archivos .py en la carpeta tools/
    for file_path in tools_dir.glob("*.py"):
        # Ignorar archivos especiales
        if file_path.name == "__init__.py":
            continue

        module_name = file_path.stem  # Nombre sin .py

        try:
            # Importar el módulo dinámicamente
            module = importlib.import_module(f".{module_name}", package="agent_ia_core.chatbots.etapes_classification_taric.tools")

            # Verificar que tenga TOOL_DEFINITION
            if not hasattr(module, "TOOL_DEFINITION"):
                logger.warning(f"[TARIC TOOLS] {module_name}.py no tiene TOOL_DEFINITION, ignorando...")
                continue

            tool_def = module.TOOL_DEFINITION

            # Convertir dict a ToolDefinition si es necesario (formato legacy)
            if isinstance(tool_def, dict):
                tool_def = ToolDefinition(
                    name=tool_def.get('name', module_name),
                    description=tool_def.get('description', ''),
                    parameters=tool_def.get('parameters', {}),
                    function=tool_def.get('function'),
                    category=tool_def.get('category', 'classification')
                )
            elif not isinstance(tool_def, ToolDefinition):
                logger.warning(f"[TARIC TOOLS] {module_name}.py tiene TOOL_DEFINITION inválido, ignorando...")
                continue

            # Verificar que tenga función asignada
            if tool_def.function is None:
                logger.error(f"[TARIC TOOLS] {module_name}.py: TOOL_DEFINITION.function es None")
                continue

            tools.append(tool_def)
            logger.info(f"[TARIC TOOLS] Tool autodescubierta: {tool_def.name} ({tool_def.category})")

        except Exception as e:
            logger.error(f"[TARIC TOOLS] No se pudo cargar {module_name}.py: {e}")

    return tools


# Ejecutar autodiscovery al importar el módulo
ALL_TOOLS = autodiscover_tools()

logger.info(f"\n[TARIC TOOLS] Total de tools autodescubiertas: {len(ALL_TOOLS)}")
for tool in ALL_TOOLS:
    logger.info(f"  - {tool.name}: {tool.description[:60]}...")

__all__ = ['ALL_TOOLS', 'autodiscover_tools']
