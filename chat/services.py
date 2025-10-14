"""
Service layer for integrating Agent_IA with Chat functionality
"""
import os
import sys
from typing import Dict, Any, List
from django.conf import settings

# Add agent_ia_core to Python path
agent_ia_path = os.path.join(settings.BASE_DIR, 'agent_ia_core')
if agent_ia_path not in sys.path:
    sys.path.insert(0, agent_ia_path)


class ChatAgentService:
    """Service to interact with the Agent_IA RAG system"""

    def __init__(self, user):
        """
        Initialize the chat agent service

        Args:
            user: Django User instance with llm_api_key
        """
        self.user = user
        self.api_key = user.llm_api_key

    def _get_agent_graph(self):
        """
        Initialize and return the agent graph
        Returns the compiled graph for processing queries
        """
        try:
            from agent_graph import create_agent_graph

            # Set API key temporarily for this operation
            original_key = os.environ.get('GOOGLE_API_KEY')
            if self.api_key:
                os.environ['GOOGLE_API_KEY'] = self.api_key

            try:
                graph = create_agent_graph()
                return graph
            finally:
                # Restore original key
                if original_key:
                    os.environ['GOOGLE_API_KEY'] = original_key
                elif 'GOOGLE_API_KEY' in os.environ:
                    del os.environ['GOOGLE_API_KEY']

        except ImportError as e:
            raise Exception(f"Error importing agent_graph: {e}")
        except Exception as e:
            raise Exception(f"Error creating agent graph: {e}")

    def process_message(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Process a user message through the Agent_IA system

        Args:
            message: User's question/message
            conversation_history: Previous messages in the conversation

        Returns:
            Dict with:
                - content: Agent's response
                - metadata: Information about the response (route, documents, etc.)
        """
        if not self.api_key:
            return {
                'content': 'Por favor, configura tu API key de Google Gemini en tu perfil de usuario para usar el chat IA.',
                'metadata': {
                    'error': 'NO_API_KEY',
                    'route': 'error',
                    'documents_used': [],
                    'verified_fields': [],
                    'tokens_used': 0
                }
            }

        try:
            # Get the agent graph
            graph = self._get_agent_graph()

            # Prepare the input state
            state = {
                'question': message,
                'conversation_history': conversation_history or []
            }

            # Set API key in environment
            original_key = os.environ.get('GOOGLE_API_KEY')
            if self.api_key:
                os.environ['GOOGLE_API_KEY'] = self.api_key

            try:
                # Invoke the graph
                result = graph.invoke(state)

                # Extract response and metadata
                response_content = result.get('generation', 'No se pudo generar una respuesta.')

                # Extract metadata
                metadata = {
                    'route': result.get('route_decision', 'unknown'),
                    'documents_used': [
                        {
                            'id': doc.metadata.get('ojs_notice_id', 'unknown'),
                            'title': doc.metadata.get('title', 'Sin título')
                        }
                        for doc in result.get('documents', [])
                    ],
                    'verified_fields': result.get('verified_fields', []),
                    'tokens_used': result.get('tokens_used', 0)
                }

                return {
                    'content': response_content,
                    'metadata': metadata
                }

            finally:
                # Restore original key
                if original_key:
                    os.environ['GOOGLE_API_KEY'] = original_key
                elif 'GOOGLE_API_KEY' in os.environ:
                    del os.environ['GOOGLE_API_KEY']

        except Exception as e:
            return {
                'content': f'Lo siento, ocurrió un error al procesar tu mensaje: {str(e)}',
                'metadata': {
                    'error': str(e),
                    'route': 'error',
                    'documents_used': [],
                    'verified_fields': [],
                    'tokens_used': 0
                }
            }

    def get_tender_details(self, ojs_notice_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific tender using the agent

        Args:
            ojs_notice_id: The OJS notice ID of the tender

        Returns:
            Dict with tender information
        """
        question = f"Dame toda la información detallada sobre la licitación con ID {ojs_notice_id}"
        return self.process_message(question)
