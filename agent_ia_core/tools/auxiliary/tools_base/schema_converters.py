# -*- coding: utf-8 -*-
"""
Utilidades para convertir schemas de tools entre diferentes formatos.
Soporta: Ollama, OpenAI, y Google Gemini.
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class SchemaConverter:
    """Convierte schemas de tools entre diferentes formatos de LLM providers."""

    @staticmethod
    def to_openai_format(base_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte un schema base al formato de OpenAI Function Calling.

        OpenAI espera:
        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        }

        Args:
            base_schema: Schema en formato estándar

        Returns:
            Schema en formato OpenAI
        """
        return {
            "type": "function",
            "function": {
                "name": base_schema.get("name"),
                "description": base_schema.get("description"),
                "parameters": base_schema.get("parameters", {})
            }
        }

    @staticmethod
    def to_gemini_format(base_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte un schema base al formato de Google Gemini Function Calling.

        Gemini espera un formato similar pero con algunas diferencias:
        - Usa "function_declarations" en lugar de "tools"
        - Estructura ligeramente diferente para parameters

        Args:
            base_schema: Schema en formato estándar

        Returns:
            Schema en formato Gemini
        """
        parameters = base_schema.get("parameters", {})

        # Gemini requiere convertir tipos de JSON Schema a tipos de Gemini
        gemini_properties = {}
        if "properties" in parameters:
            for prop_name, prop_def in parameters["properties"].items():
                gemini_properties[prop_name] = SchemaConverter._convert_type_to_gemini(prop_def)

        return {
            "name": base_schema.get("name"),
            "description": base_schema.get("description"),
            "parameters": {
                "type": "object",
                "properties": gemini_properties,
                "required": parameters.get("required", [])
            }
        }

    @staticmethod
    def to_ollama_format(base_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte un schema base al formato de Ollama Function Calling.

        Ollama usa un formato similar a OpenAI.

        Args:
            base_schema: Schema en formato estándar

        Returns:
            Schema en formato Ollama
        """
        return {
            "type": "function",
            "function": base_schema
        }

    @staticmethod
    def _convert_type_to_gemini(prop_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte definiciones de tipos de JSON Schema a formato Gemini.

        Gemini usa tipos: STRING, INTEGER, NUMBER, BOOLEAN, ARRAY, OBJECT

        Args:
            prop_def: Definición de propiedad en JSON Schema

        Returns:
            Definición de propiedad en formato Gemini
        """
        json_type = prop_def.get("type", "string")

        # Mapeo de tipos JSON Schema a Gemini
        type_mapping = {
            "string": "STRING",
            "integer": "INTEGER",
            "number": "NUMBER",
            "boolean": "BOOLEAN",
            "array": "ARRAY",
            "object": "OBJECT"
        }

        gemini_type = type_mapping.get(json_type, "STRING")

        result = {
            "type": gemini_type,
            "description": prop_def.get("description", "")
        }

        # Manejar arrays
        if json_type == "array" and "items" in prop_def:
            result["items"] = SchemaConverter._convert_type_to_gemini(prop_def["items"])

        return result


class ToolCallConverter:
    """Convierte tool calls entre diferentes formatos de LLM providers."""

    @staticmethod
    def from_openai_tool_call(tool_call: Any) -> Dict[str, Any]:
        """
        Convierte un tool call de OpenAI al formato estándar.

        OpenAI devuelve:
        tool_call.function.name
        tool_call.function.arguments (JSON string)

        Args:
            tool_call: Tool call de OpenAI

        Returns:
            Dict en formato estándar: {'function': {'name': '...', 'arguments': {...}}}
        """
        import json

        try:
            arguments = json.loads(tool_call.function.arguments)
        except (json.JSONDecodeError, AttributeError):
            arguments = {}

        return {
            "function": {
                "name": tool_call.function.name,
                "arguments": arguments
            }
        }

    @staticmethod
    def from_gemini_tool_call(tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte un tool call de Gemini al formato estándar.

        Gemini devuelve:
        {
            "function_call": {
                "name": "...",
                "args": {...}
            }
        }

        Args:
            tool_call: Tool call de Gemini

        Returns:
            Dict en formato estándar: {'function': {'name': '...', 'arguments': {...}}}
        """
        function_call = tool_call.get("function_call", {})

        return {
            "function": {
                "name": function_call.get("name", ""),
                "arguments": function_call.get("args", {})
            }
        }

    @staticmethod
    def from_ollama_tool_call(tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte un tool call de Ollama al formato estándar.

        Ollama ya usa un formato estándar similar a OpenAI.

        Args:
            tool_call: Tool call de Ollama

        Returns:
            Dict en formato estándar: {'function': {'name': '...', 'arguments': {...}}}
        """
        # Ollama ya usa el formato estándar
        return tool_call


def convert_tools_for_provider(tools: List[Any], provider: str) -> List[Dict[str, Any]]:
    """
    Convierte una lista de tools al formato del proveedor especificado.

    Args:
        tools: Lista de objetos BaseTool
        provider: Proveedor ("ollama", "openai", "google")

    Returns:
        Lista de tools en el formato correcto para el proveedor
    """
    converted_tools = []

    for tool in tools:
        base_schema = tool.get_schema()

        if provider == "ollama":
            converted_tools.append(SchemaConverter.to_ollama_format(base_schema))
        elif provider == "openai":
            converted_tools.append(SchemaConverter.to_openai_format(base_schema))
        elif provider == "google":
            converted_tools.append(SchemaConverter.to_gemini_format(base_schema))
        else:
            logger.warning(f"Proveedor desconocido: {provider}, usando formato Ollama")
            converted_tools.append(SchemaConverter.to_ollama_format(base_schema))

    return converted_tools
