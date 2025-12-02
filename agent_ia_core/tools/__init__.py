"""
Autodiscovery de tools.

Este módulo detecta AUTOMÁTICAMENTE todos los archivos .py en la carpeta tools/
(excepto __init__.py, base.py, y la carpeta auxiliary/) y registra sus TOOL_DEFINITION.

Para agregar una nueva tool:
1. Crear archivo `nombre_tool.py` en esta carpeta
2. Definir `TOOL_DEFINITION` con ToolDefinition
3. ¡Listo! Se autodescubre automáticamente
"""

import os
import importlib
from pathlib import Path
from typing import List
from .auxiliary.tools_base import ToolDefinition
import logging

logger = logging.getLogger(__name__)

# Lista de todos los ToolDefinition autodescubiertos
ALL_TOOLS: List[ToolDefinition] = []


def autodiscover_tools() -> List[ToolDefinition]:
    """
    Descubre automáticamente todas las tools en la carpeta tools/.

    Reglas:
    - Cada archivo .py (excepto __init__, base, y auxiliary/*) debe tener TOOL_DEFINITION
    - TOOL_DEFINITION debe ser una instancia de ToolDefinition
    - El nombre del archivo debe coincidir con tool.name

    Returns:
        Lista de ToolDefinition encontradas
    """
    tools = []
    tools_dir = Path(__file__).parent

    logger.info("[AUTODISCOVERY] Escaneando tools...")

    # Obtener todos los archivos .py en la carpeta tools/
    for file_path in tools_dir.glob("*.py"):
        # Ignorar archivos especiales
        if file_path.name == "__init__.py":
            continue

        module_name = file_path.stem  # Nombre sin .py

        try:
            # Importar el módulo dinámicamente
            module = importlib.import_module(f".{module_name}", package="agent_ia_core.tools")

            # Verificar que tenga TOOL_DEFINITION
            if not hasattr(module, "TOOL_DEFINITION"):
                logger.warning(f"[AUTODISCOVERY] ⚠️  {module_name}.py no tiene TOOL_DEFINITION, ignorando...")
                continue

            tool_def = module.TOOL_DEFINITION

            # Verificar que sea ToolDefinition
            if not isinstance(tool_def, ToolDefinition):
                logger.warning(f"[AUTODISCOVERY] ⚠️  {module_name}.py tiene TOOL_DEFINITION inválido, ignorando...")
                continue

            # Verificar que el nombre coincida con el archivo (opcional pero recomendado)
            if tool_def.name != module_name:
                logger.warning(
                    f"[AUTODISCOVERY] ⚠️  {module_name}.py: nombre de tool '{tool_def.name}' "
                    f"no coincide con nombre de archivo '{module_name}'"
                )

            # Verificar que tenga función asignada
            if tool_def.function is None:
                logger.error(f"[AUTODISCOVERY] ❌ {module_name}.py: TOOL_DEFINITION.function es None")
                continue

            tools.append(tool_def)
            logger.info(f"[AUTODISCOVERY] ✓ Tool autodescubierta: {tool_def.name} ({tool_def.category})")

        except Exception as e:
            logger.error(f"[AUTODISCOVERY] ❌ No se pudo cargar {module_name}.py: {e}")

    return tools


# Ejecutar autodiscovery al importar el módulo
ALL_TOOLS = autodiscover_tools()

logger.info(f"\n[AUTODISCOVERY] ✅ Total de tools autodescubiertas: {len(ALL_TOOLS)}")
for tool in ALL_TOOLS:
    logger.info(f"  - {tool.name}: {tool.description[:60]}...")

# Exportar clases base desde tools_base
from .auxiliary.tools_base import ToolDefinition, ToolRegistry

__all__ = ['ALL_TOOLS', 'ToolDefinition', 'ToolRegistry', 'autodiscover_tools']
