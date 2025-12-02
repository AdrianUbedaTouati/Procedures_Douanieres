# -*- coding: utf-8 -*-
"""
Definición base para herramientas del agente.

Esta es la ÚNICA FUENTE DE VERDAD para cada tool:
- Nombre, descripción y parámetros se definen una sola vez aquí
- Se usa en LLM principal (OpenAI/Gemini function calling)
- Se usa en Response Reviewer (prompt con herramientas disponibles)
- Se usa en Logs (registro de tools con descripciones)
"""

from dataclasses import dataclass
from typing import Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """
    Definición completa de una herramienta del agente.

    Esta clase centraliza TODA la información de una tool en un solo lugar.
    El sistema usa autodiscovery: cada archivo .py en tools/ (excepto __init__, base, auxiliary/)
    debe exportar una variable TOOL_DEFINITION de este tipo.

    Atributos:
        name: Nombre único de la función (debe coincidir con el nombre del archivo .py)
        description: Descripción para el LLM (UNA SOLA FUENTE DE VERDAD)
        parameters: JSON Schema de parámetros (compatible con OpenAI/Gemini)
        function: Función Python real a ejecutar
        category: Categoría opcional para organización (search, detail, company, etc.)

    Example:
        ```python
        # En find_best_tender.py:
        TOOL_DEFINITION = ToolDefinition(
            name="find_best_tender",
            description="Encuentra LA mejor licitación...",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "..."}
                },
                "required": ["query"]
            },
            function=find_best_tender_impl,
            category="search"
        )
        ```
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable
    category: str = "general"

    def to_openai_format(self) -> Dict[str, Any]:
        """
        Convierte la definición a formato OpenAI function calling.

        Returns:
            Dict con formato:
            {
                "type": "function",
                "function": {
                    "name": "...",
                    "description": "...",
                    "parameters": {...}
                }
            }
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def to_gemini_format(self) -> Dict[str, Any]:
        """
        Convierte la definición a formato Gemini function calling.

        Returns:
            Dict con formato:
            {
                "name": "...",
                "description": "...",
                "parameters": {...}
            }
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

    def get_reviewer_format(self) -> str:
        """
        Genera formato de texto para mostrar en el prompt del reviewer.
        Extrae automáticamente los parámetros del schema JSON.
        Trunca la descripción a la primera línea o primeras 150 caracteres.

        Returns:
            String con formato: "- nombre(param1: type, param2: type): descripción breve"

        Example:
            "- find_best_tender(query: string): Encuentra LA mejor licitación..."
        """
        params = []
        if "properties" in self.parameters:
            for param_name, param_info in self.parameters["properties"].items():
                param_type = param_info.get("type", "any")
                params.append(f"{param_name}: {param_type}")

        params_str = ", ".join(params) if params else ""

        # Extraer solo la primera línea o primera oración de la descripción
        # Eliminar saltos de línea y limitar a 200 caracteres
        short_desc = self.description.split('\n')[0].strip()
        if len(short_desc) > 200:
            short_desc = short_desc[:197] + "..."

        return f"- {self.name}({params_str}): {short_desc}"

    def __repr__(self):
        return f"<ToolDefinition(name='{self.name}', category='{self.category}')>"
