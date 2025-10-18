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
            user: Django User instance with llm_api_key and llm_provider
        """
        self.user = user
        self.api_key = user.llm_api_key
        self.provider = user.llm_provider if hasattr(user, 'llm_provider') else 'gemini'
        self._agent = None

    def _get_agent(self):
        """
        Initialize and return the EFormsRAGAgent
        Cached per service instance
        """
        if self._agent is not None:
            return self._agent

        if not self.api_key:
            raise ValueError("No API key configured for user")

        try:
            # Import agent_graph module
            from agent_ia_core import agent_graph
            from agent_ia_core import config

            # Map provider names to agent_graph format
            provider_map = {
                'gemini': ('google', 'gemini-2.0-flash-exp'),
                'openai': ('openai', 'gpt-4o-mini'),
                'nvidia': ('nvidia', 'meta/llama-3.1-8b-instruct')
            }

            agent_provider, model_name = provider_map.get(
                self.provider,
                ('google', 'gemini-2.0-flash-exp')
            )

            # Create agent instance with user's API key and provider
            self._agent = agent_graph.EFormsRAGAgent(
                api_key=self.api_key,
                llm_provider=agent_provider,
                llm_model=model_name,
                temperature=0.3,
                k_retrieve=6,
                use_grading=False,  # Disabled: grading too strict with NVIDIA
                use_verification=False  # Disable verification for faster responses
            )

            return self._agent

        except ImportError as e:
            raise Exception(f"Error importing agent modules: {e}")
        except Exception as e:
            raise Exception(f"Error creating agent: {e}")

    def process_message(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Process a user message through the Agent_IA system

        Args:
            message: User's question/message
            conversation_history: Previous messages in the conversation (not used yet)

        Returns:
            Dict with:
                - content: Agent's response
                - metadata: Information about the response (route, documents, tokens, cost, etc.)
        """
        if not self.api_key:
            return {
                'content': 'Por favor, configura tu API key de LLM en tu perfil de usuario para usar el chat IA.',
                'metadata': {
                    'error': 'NO_API_KEY',
                    'route': 'error',
                    'documents_used': [],
                    'verified_fields': [],
                    'iterations': 0,
                    'total_tokens': 0,
                    'cost_eur': 0.0
                }
            }

        try:
            # Get the agent
            agent = self._get_agent()

            # Verify agent was created successfully
            if agent is None:
                raise ValueError("El agente no pudo ser inicializado correctamente")

            if not hasattr(agent, 'query') or not callable(agent.query):
                raise AttributeError(f"El agente no tiene un método 'query' válido. Tipo: {type(agent)}")

            # Set API key in environment for this request
            env_var_map = {
                'gemini': 'GOOGLE_API_KEY',
                'openai': 'OPENAI_API_KEY',
                'nvidia': 'NVIDIA_API_KEY'
            }
            env_var = env_var_map.get(self.provider, 'GOOGLE_API_KEY')
            os.environ[env_var] = self.api_key

            # Execute query through the agent
            result = agent.query(message)

            # Extract response content
            response_content = result.get('answer', 'No se pudo generar una respuesta.')

            # Format document metadata for frontend
            documents_used = [
                {
                    'id': doc.get('ojs_notice_id', 'unknown'),
                    'section': doc.get('section', 'unknown'),
                    'content_preview': doc.get('content', '')[:150] + '...'
                }
                for doc in result.get('documents', [])
            ]

            # Calculate token usage and cost
            from core.token_pricing import calculate_chat_cost

            # Prepare full input (includes retrieved documents in the context)
            full_input = message
            if documents_used:
                # Approximate: add document content to input token count
                docs_text = '\n'.join([doc.get('content_preview', '') for doc in documents_used])
                full_input = f"{message}\n\nContext:\n{docs_text}"

            cost_data = calculate_chat_cost(
                input_text=full_input,
                output_text=response_content,
                provider=self.provider
            )

            # Build metadata response with token/cost info
            metadata = {
                'route': result.get('route', 'unknown'),
                'documents_used': documents_used,
                'verified_fields': result.get('verified_fields', []),
                'iterations': result.get('iterations', 0),
                'num_documents': len(documents_used),
                # Token and cost tracking
                'input_tokens': cost_data['input_tokens'],
                'output_tokens': cost_data['output_tokens'],
                'total_tokens': cost_data['total_tokens'],
                'cost_eur': cost_data['total_cost_eur']
            }

            return {
                'content': response_content,
                'metadata': metadata
            }

        except ValueError as e:
            # API key or configuration error
            return {
                'content': f'Error de configuración: {str(e)}',
                'metadata': {
                    'error': 'CONFIGURATION_ERROR',
                    'route': 'error',
                    'documents_used': [],
                    'verified_fields': [],
                    'iterations': 0
                }
            }

        except Exception as e:
            # General error
            error_msg = str(e)

            # Check for specific error types
            if 'ChromaDB' in error_msg or 'collection' in error_msg.lower():
                error_msg = (
                    'El sistema de búsqueda no está inicializado. '
                    'Por favor, ve a la sección de "Vectorización" para indexar '
                    'las licitaciones antes de usar el chat.'
                )

            return {
                'content': f'Lo siento, ocurrió un error al procesar tu mensaje: {error_msg}',
                'metadata': {
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'route': 'error',
                    'documents_used': [],
                    'verified_fields': [],
                    'iterations': 0
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

    def reset_agent(self):
        """
        Reset the cached agent instance
        Useful when configuration changes or to free memory
        """
        self._agent = None
