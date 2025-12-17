"""
Tests para agent_ia_core.
Verifica el agente de function calling y las tools.
"""
import pytest
from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Añadir el path del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ToolRegistryTests(TestCase):
    """Tests para el registro de tools."""

    def test_tool_registry_import(self):
        """Test que ToolRegistry se puede importar."""
        try:
            from agent_ia_core.tools import ToolRegistry
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"No se pudo importar ToolRegistry: {e}")

    def test_all_tools_import(self):
        """Test que ALL_TOOLS se puede importar."""
        try:
            from agent_ia_core.tools import ALL_TOOLS
            self.assertIsInstance(ALL_TOOLS, list)
        except ImportError as e:
            self.fail(f"No se pudo importar ALL_TOOLS: {e}")

    def test_web_search_tool_exists(self):
        """Test que la tool web_search existe."""
        from agent_ia_core.tools import ALL_TOOLS
        tool_names = [tool.name for tool in ALL_TOOLS]
        self.assertIn('web_search', tool_names)

    def test_browse_webpage_tool_exists(self):
        """Test que la tool browse_webpage existe."""
        from agent_ia_core.tools import ALL_TOOLS
        tool_names = [tool.name for tool in ALL_TOOLS]
        self.assertIn('browse_webpage', tool_names)

    def test_no_tender_tools_exist(self):
        """Test que no existen tools de licitaciones."""
        from agent_ia_core.tools import ALL_TOOLS
        tool_names = [tool.name for tool in ALL_TOOLS]
        tender_tools = [
            'find_by_cpv',
            'find_by_budget',
            'find_by_deadline',
            'find_by_location',
            'get_tender_details',
            'get_tender_xml',
            'search_tenders',
            'get_tenders_summary',
            'get_company_info'
        ]
        for tool in tender_tools:
            self.assertNotIn(tool, tool_names, f"Tool {tool} no debería existir")


class FunctionCallingAgentTests(TestCase):
    """Tests para FunctionCallingAgent."""

    def test_agent_import(self):
        """Test que FunctionCallingAgent se puede importar."""
        try:
            from agent_ia_core.agent_function_calling import FunctionCallingAgent
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"No se pudo importar FunctionCallingAgent: {e}")

    def test_agent_requires_api_key_for_cloud_providers(self):
        """Test que el agente requiere API key para proveedores cloud."""
        from agent_ia_core.agent_function_calling import FunctionCallingAgent

        with self.assertRaises(ValueError):
            FunctionCallingAgent(
                llm_provider='openai',
                llm_model='gpt-4o',
                llm_api_key=None  # Sin API key
            )

    def test_agent_accepts_ollama_without_api_key(self):
        """Test que el agente acepta Ollama sin API key."""
        from agent_ia_core.agent_function_calling import FunctionCallingAgent

        # Esto debería fallar solo por conexión a Ollama, no por API key
        try:
            agent = FunctionCallingAgent(
                llm_provider='ollama',
                llm_model='test-model',
                llm_api_key=None
            )
            # Si llegamos aquí sin error de API key, el test pasa
            self.assertTrue(True)
        except ValueError as e:
            if 'API key' in str(e):
                self.fail("No debería requerir API key para Ollama")
            # Otros errores (como conexión) son esperados
        except Exception:
            # Otros errores (como conexión) son esperados
            pass

    def test_agent_invalid_provider_raises_error(self):
        """Test que proveedor inválido lanza error."""
        from agent_ia_core.agent_function_calling import FunctionCallingAgent

        with self.assertRaises(ValueError):
            FunctionCallingAgent(
                llm_provider='invalid_provider',
                llm_model='some-model',
                llm_api_key='test-key'
            )


class PromptsTests(TestCase):
    """Tests para el sistema de prompts."""

    def test_prompts_import(self):
        """Test que prompts.py se puede importar."""
        try:
            from agent_ia_core.prompts import prompts
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"No se pudo importar prompts: {e}")

    def test_system_prompt_exists(self):
        """Test que SYSTEM_PROMPT existe."""
        from agent_ia_core.prompts.prompts import SYSTEM_PROMPT
        self.assertIsInstance(SYSTEM_PROMPT, str)
        self.assertGreater(len(SYSTEM_PROMPT), 100)

    def test_system_prompt_is_generic(self):
        """Test que el system prompt es genérico (sin licitaciones)."""
        from agent_ia_core.prompts.prompts import SYSTEM_PROMPT
        # No debería contener referencias a licitaciones
        self.assertNotIn('licitacion', SYSTEM_PROMPT.lower())
        self.assertNotIn('tender', SYSTEM_PROMPT.lower())
        self.assertNotIn('TED', SYSTEM_PROMPT)

    def test_routing_system_prompt_exists(self):
        """Test que ROUTING_SYSTEM_PROMPT existe."""
        from agent_ia_core.prompts.prompts import ROUTING_SYSTEM_PROMPT
        self.assertIsInstance(ROUTING_SYSTEM_PROMPT, str)

    def test_create_answer_prompt_function(self):
        """Test que create_answer_prompt funciona."""
        from agent_ia_core.prompts.prompts import create_answer_prompt
        prompt = create_answer_prompt("¿Qué tiempo hace?", [])
        self.assertIsInstance(prompt, str)
        self.assertIn("¿Qué tiempo hace?", prompt)


class WebSearchToolTests(TestCase):
    """Tests para la tool web_search."""

    def test_web_search_tool_definition(self):
        """Test que web_search tiene definición correcta."""
        from agent_ia_core.tools import ALL_TOOLS
        web_search = None
        for tool in ALL_TOOLS:
            if tool.name == 'web_search':
                web_search = tool
                break
        self.assertIsNotNone(web_search)

    def test_web_search_has_required_fields(self):
        """Test que web_search tiene campos requeridos."""
        from agent_ia_core.tools import ALL_TOOLS
        web_search = None
        for tool in ALL_TOOLS:
            if tool.name == 'web_search':
                web_search = tool
                break

        # Verificar que tiene los atributos necesarios
        self.assertIsNotNone(web_search)
        self.assertTrue(hasattr(web_search, 'name'))
        self.assertTrue(hasattr(web_search, 'description'))
        self.assertTrue(hasattr(web_search, 'function'))


class BrowseWebpageToolTests(TestCase):
    """Tests para la tool browse_webpage."""

    def test_browse_webpage_tool_definition(self):
        """Test que browse_webpage tiene definición correcta."""
        from agent_ia_core.tools import ALL_TOOLS
        browse = None
        for tool in ALL_TOOLS:
            if tool.name == 'browse_webpage':
                browse = tool
                break
        self.assertIsNotNone(browse)


class GetCurrentDatetimeTests(TestCase):
    """Tests para la función get_current_datetime."""

    def test_get_current_datetime_returns_string(self):
        """Test que get_current_datetime devuelve string."""
        from agent_ia_core.agent_function_calling import get_current_datetime
        result = get_current_datetime()
        self.assertIsInstance(result, str)

    def test_get_current_datetime_format(self):
        """Test que get_current_datetime tiene formato correcto."""
        from agent_ia_core.agent_function_calling import get_current_datetime
        result = get_current_datetime()
        self.assertIn('Fecha actual:', result)
        self.assertIn('Hora:', result)


class ChatServiceTests(TestCase):
    """Tests para ChatAgentService."""

    def test_chat_service_import(self):
        """Test que ChatAgentService se puede importar."""
        try:
            from apps.chat.services import ChatAgentService
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"No se pudo importar ChatAgentService: {e}")

    def test_chat_service_init(self):
        """Test inicialización de ChatAgentService."""
        from apps.chat.services import ChatAgentService
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            llm_provider='gemini',
            llm_api_key='test-key'
        )

        service = ChatAgentService(user)
        self.assertEqual(service.provider, 'gemini')
        self.assertEqual(service.api_key, 'test-key')

    def test_chat_service_returns_error_without_api_key(self):
        """Test que el servicio devuelve error sin API key."""
        from apps.chat.services import ChatAgentService
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123',
            llm_provider='openai',
            llm_api_key=''  # Sin API key
        )

        service = ChatAgentService(user)
        result = service.process_message("Hola")

        # Debería devolver error de configuración
        self.assertIn('error', result['metadata'])


class ResponseReviewerTests(TestCase):
    """Tests para ResponseReviewer."""

    def test_response_reviewer_import(self):
        """Test que ResponseReviewer se puede importar."""
        try:
            from apps.chat.response_reviewer import ResponseReviewer
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"No se pudo importar ResponseReviewer: {e}")
