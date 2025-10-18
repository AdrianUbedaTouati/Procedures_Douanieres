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
            user: Django User instance with llm_api_key, llm_provider, ollama_model, ollama_embedding_model
        """
        self.user = user
        self.api_key = user.llm_api_key if hasattr(user, 'llm_api_key') else None
        self.provider = user.llm_provider if hasattr(user, 'llm_provider') else 'gemini'
        self.ollama_model = user.ollama_model if hasattr(user, 'ollama_model') else 'qwen2.5:72b'
        self.ollama_embedding_model = user.ollama_embedding_model if hasattr(user, 'ollama_embedding_model') else 'nomic-embed-text'
        self._agent = None

    def _get_agent(self):
        """
        Initialize and return the EFormsRAGAgent
        Cached per service instance
        """
        if self._agent is not None:
            return self._agent

        # Ollama doesn't need API key
        if not self.api_key and self.provider != 'ollama':
            raise ValueError("No API key configured for user")

        try:
            # Import agent_graph module
            from agent_ia_core import agent_graph
            from agent_ia_core import config

            # Map provider names to agent_graph format
            provider_map = {
                'gemini': ('google', 'gemini-2.0-flash-exp'),
                'openai': ('openai', 'gpt-4o-mini'),
                'nvidia': ('nvidia', 'meta/llama-3.1-8b-instruct'),
                'ollama': ('ollama', self.ollama_model)  # Use user's configured model
            }

            # IMPORTANTE: NO usar fallback. Si el provider no está en el map, es un error.
            # Esto asegura que siempre se use la configuración del perfil del usuario.
            if self.provider not in provider_map:
                raise ValueError(
                    f"Proveedor LLM no válido: '{self.provider}'. "
                    f"Por favor, ve a tu perfil y selecciona un proveedor válido: "
                    f"{', '.join(provider_map.keys())}"
                )

            agent_provider, model_name = provider_map[self.provider]

            # Create agent instance with user's API key and provider
            if self.provider == 'ollama':
                # Verificar que Ollama está disponible antes de crear el agente
                import requests
                try:
                    response = requests.get('http://localhost:11434/api/tags', timeout=2)
                    if response.status_code != 200:
                        raise ValueError("Ollama no está respondiendo correctamente en http://localhost:11434")

                    # Verificar que el modelo está descargado
                    models = response.json().get('models', [])
                    model_names = [m['name'] for m in models]
                    if model_name not in model_names:
                        available = ', '.join(model_names[:5]) if model_names else 'ninguno'
                        raise ValueError(
                            f"El modelo '{model_name}' no está descargado en Ollama. "
                            f"Modelos disponibles: {available}. "
                            f"Descárgalo con: ollama pull {model_name}"
                        )
                except requests.exceptions.ConnectionError:
                    raise ValueError(
                        "No se puede conectar con Ollama. "
                        "Verifica que Ollama esté ejecutándose: ollama serve"
                    )
                except requests.exceptions.Timeout:
                    raise ValueError("Timeout al conectar con Ollama. Verifica que esté funcionando correctamente.")

                # Ollama doesn't need API key
                self._agent = agent_graph.EFormsRAGAgent(
                    api_key=None,  # No API key for Ollama
                    llm_provider=agent_provider,
                    llm_model=model_name,
                    ollama_embedding_model=self.ollama_embedding_model,
                    temperature=0.3,
                    k_retrieve=6,
                    use_grading=self.user.use_grading if hasattr(self.user, 'use_grading') else False,
                    use_verification=self.user.use_verification if hasattr(self.user, 'use_verification') else False
                )
            else:
                # Cloud providers need API key
                self._agent = agent_graph.EFormsRAGAgent(
                    api_key=self.api_key,
                    llm_provider=agent_provider,
                    llm_model=model_name,
                    temperature=0.3,
                    k_retrieve=6,
                    use_grading=self.user.use_grading if hasattr(self.user, 'use_grading') else False,
                    use_verification=self.user.use_verification if hasattr(self.user, 'use_verification') else False
                )

            return self._agent

        except ImportError as e:
            raise Exception(f"Error importing agent modules: {e}")
        except Exception as e:
            raise Exception(f"Error creating agent: {e}")

    def _enrich_with_company_context(self, message: str) -> str:
        """
        Enrich user message with company profile context for better recommendations

        Args:
            message: Original user message

        Returns:
            Enriched message with company context prepended
        """
        try:
            from company.models import CompanyProfile

            # Try to get company profile
            profile = CompanyProfile.objects.filter(user=self.user).first()

            if not profile:
                # No profile, return original message
                return message

            # Build company context
            context_parts = []
            context_parts.append("CONTEXTO DE MI EMPRESA:")

            if profile.company_name:
                context_parts.append(f"- Nombre: {profile.company_name}")

            if profile.sector:
                context_parts.append(f"- Sector: {profile.sector}")

            if profile.cpv_codes:
                context_parts.append(f"- Códigos CPV de interés: {', '.join(profile.cpv_codes[:5])}")

            if profile.capabilities:
                context_parts.append(f"- Capacidades: {profile.capabilities}")

            if profile.certifications:
                context_parts.append(f"- Certificaciones: {', '.join(profile.certifications[:3])}")

            if profile.geographic_scope:
                context_parts.append(f"- Ámbito geográfico: {', '.join(profile.geographic_scope[:3])}")

            if profile.min_budget or profile.max_budget:
                budget_range = f"{profile.min_budget or 0} - {profile.max_budget or 'sin límite'} EUR"
                context_parts.append(f"- Rango presupuesto: {budget_range}")

            # Append original message
            context_parts.append("")
            context_parts.append(f"PREGUNTA: {message}")

            return "\n".join(context_parts)

        except Exception as e:
            # If anything fails, just return original message
            return message

    def process_message(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Process a user message through the Agent_IA system

        Args:
            message: User's question/message
            conversation_history: Previous messages in the conversation (list of dicts with 'role' and 'content')
                                  Limited to last 10 messages to avoid token overflow

        Returns:
            Dict with:
                - content: Agent's response
                - metadata: Information about the response (route, documents, tokens, cost, etc.)
        """
        # Ollama doesn't need API key, check only for cloud providers
        if not self.api_key and self.provider != 'ollama':
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
            import sys

            # Log inicio del proceso
            print(f"\n[SERVICE] Iniciando process_message...", file=sys.stderr)
            print(f"[SERVICE] Proveedor: {self.provider.upper()}", file=sys.stderr)
            if self.provider == 'ollama':
                print(f"[SERVICE] Modelo LLM: {self.ollama_model}", file=sys.stderr)
                print(f"[SERVICE] Modelo Embeddings: {self.ollama_embedding_model}", file=sys.stderr)
            print(f"[SERVICE] Mensaje: {message[:60]}...", file=sys.stderr)

            # Get the agent
            print(f"[SERVICE] Creando agente RAG...", file=sys.stderr)
            agent = self._get_agent()

            # Verify agent was created successfully
            if agent is None:
                raise ValueError("El agente no pudo ser inicializado correctamente")

            if not hasattr(agent, 'query') or not callable(agent.query):
                raise AttributeError(f"El agente no tiene un método 'query' válido. Tipo: {type(agent)}")

            print(f"[SERVICE] ✓ Agente creado correctamente", file=sys.stderr)

            # Set API key in environment for this request
            if self.provider != 'ollama':
                env_var_map = {
                    'gemini': 'GOOGLE_API_KEY',
                    'openai': 'OPENAI_API_KEY',
                    'nvidia': 'NVIDIA_API_KEY'
                }
                env_var = env_var_map.get(self.provider, 'GOOGLE_API_KEY')
                os.environ[env_var] = self.api_key

            # Build context with conversation history
            context_message = message

            # Add conversation history if available
            if conversation_history and len(conversation_history) > 0:
                print(f"[SERVICE] Añadiendo historial de conversación ({len(conversation_history)} mensajes)...", file=sys.stderr)

                # Format history for context (limit to last 10 messages to avoid token overflow)
                recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
                history_text = "Historial de la conversación:\n"
                for msg in recent_history:
                    role_label = "Usuario" if msg['role'] == 'user' else "Asistente"
                    history_text += f"{role_label}: {msg['content']}\n"

                context_message = f"{history_text}\n---\n\nMensaje actual:\n{message}"

            # Enrich message with company profile context if asking for recommendations
            enriched_message = context_message
            recommendation_keywords = ['adecua', 'recomend', 'mejor', 'apropiada', 'conveniente', 'ideal', 'mi empresa']
            if any(keyword in message.lower() for keyword in recommendation_keywords):
                print(f"[SERVICE] Enriqueciendo mensaje con contexto de empresa...", file=sys.stderr)
                enriched_message = self._enrich_with_company_context(context_message)

            # Execute query through the agent
            print(f"[SERVICE] Ejecutando query en el agente...", file=sys.stderr)
            result = agent.query(enriched_message)
            print(f"[SERVICE] ✓ Query ejecutado correctamente", file=sys.stderr)

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

            # Log final del proceso
            print(f"[SERVICE] ✓ Respuesta procesada: {len(response_content)} caracteres", file=sys.stderr)
            print(f"[SERVICE] Documentos recuperados: {len(documents_used)}", file=sys.stderr)
            print(f"[SERVICE] Tokens totales: {cost_data['total_tokens']} (in: {cost_data['input_tokens']}, out: {cost_data['output_tokens']})", file=sys.stderr)
            print(f"[SERVICE] Costo: €{cost_data['total_cost_eur']:.4f}\n", file=sys.stderr)

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
