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

# Import logging system
from apps.core.logging_config import ChatLogger


class ChatAgentService:
    """Service to interact with the Agent_IA system"""

    def __init__(self, user, session_id=None):
        """
        Initialize the chat agent service

        Args:
            user: Django User instance with llm_api_key, llm_provider, openai_model, ollama_model, ollama_embedding_model
            session_id: Optional session ID for logging purposes
        """
        self.user = user
        self.api_key = user.llm_api_key if hasattr(user, 'llm_api_key') else None
        self.provider = user.llm_provider if hasattr(user, 'llm_provider') else 'gemini'
        self.openai_model = user.openai_model if hasattr(user, 'openai_model') else 'gpt-4o-mini'
        self.openai_embedding_model = user.openai_embedding_model if hasattr(user, 'openai_embedding_model') else 'text-embedding-3-small'
        self.ollama_model = user.ollama_model if hasattr(user, 'ollama_model') else 'qwen2.5:72b'
        self.ollama_embedding_model = user.ollama_embedding_model if hasattr(user, 'ollama_embedding_model') else 'nomic-embed-text'
        self._agent = None

        # Inicializar logger si tenemos session_id
        self.chat_logger = None
        if session_id:
            self.chat_logger = ChatLogger(session_id=session_id, user_id=user.id)

    def _get_agent(self):
        """
        Initialize and return FunctionCallingAgent
        Cached per service instance
        """
        if self._agent is not None:
            return self._agent

        # Ollama doesn't need API key
        if not self.api_key and self.provider != 'ollama':
            raise ValueError("No API key configured for user")

        return self._create_function_calling_agent()

    def _create_function_calling_agent(self):
        """
        Create and return a FunctionCallingAgent instance
        """
        try:
            from agent_ia_core import FunctionCallingAgent

            print(f"[SERVICE] Creando FunctionCallingAgent...", file=sys.stderr)
            print(f"[SERVICE] Proveedor: {self.provider}", file=sys.stderr)

            # Verificar Ollama si es necesario
            if self.provider == 'ollama':
                self._verify_ollama_availability()

            # Determinar el modelo según el proveedor
            if self.provider == 'ollama':
                model = self.ollama_model
            elif self.provider == 'openai':
                model = self.openai_model
            elif self.provider == 'google':
                model = 'gemini-2.0-flash-exp'
            else:
                model = self.ollama_model

            # Crear agente con usuario (para tools de contexto)
            self._agent = FunctionCallingAgent(
                llm_provider=self.provider,
                llm_model=model,
                llm_api_key=None if self.provider == 'ollama' else self.api_key,
                user=self.user,
                max_iterations=15,
                temperature=0.3,
                chat_logger=self.chat_logger
            )

            print(f"[SERVICE] FunctionCallingAgent creado con {len(self._agent.tool_registry.tool_definitions)} tools", file=sys.stderr)
            return self._agent

        except Exception as e:
            raise Exception(f"Error creating FunctionCallingAgent: {e}")

    def _verify_ollama_availability(self):
        """
        Verify Ollama is running and model is available
        """
        import requests
        try:
            response = requests.get('http://localhost:11434/api/tags', timeout=2)
            if response.status_code != 200:
                raise ValueError("Ollama no está respondiendo correctamente en http://localhost:11434")

            # Verificar que el modelo está descargado
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            if self.ollama_model not in model_names:
                available = ', '.join(model_names[:5]) if model_names else 'ninguno'
                raise ValueError(
                    f"El modelo '{self.ollama_model}' no está descargado en Ollama. "
                    f"Modelos disponibles: {available}. "
                    f"Descárgalo con: ollama pull {self.ollama_model}"
                )
        except requests.exceptions.ConnectionError:
            raise ValueError(
                "No se puede conectar con Ollama. "
                "Verifica que Ollama esté ejecutándose: ollama serve"
            )
        except requests.exceptions.Timeout:
            raise ValueError("Timeout al conectar con Ollama. Verifica que esté funcionando correctamente.")

    def process_message(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Process a user message through the Agent_IA system

        Args:
            message: User's question/message
            conversation_history: Previous messages in the conversation

        Returns:
            Dict with:
                - content: Agent's response
                - metadata: Information about the response
        """
        # Ollama doesn't need API key, check only for cloud providers
        if not self.api_key and self.provider != 'ollama':
            return {
                'content': 'Por favor, configura tu API key de LLM en tu perfil de usuario para usar el chat IA.',
                'metadata': {
                    'error': 'NO_API_KEY',
                    'route': 'error',
                    'documents_used': [],
                    'iterations': 0,
                    'total_tokens': 0,
                    'cost_eur': 0.0
                }
            }

        try:
            print(f"\n[SERVICE] Iniciando process_message...", file=sys.stderr)
            print(f"[SERVICE] Proveedor: {self.provider.upper()}", file=sys.stderr)
            if self.provider == 'ollama':
                print(f"[SERVICE] Modelo LLM: {self.ollama_model}", file=sys.stderr)
            print(f"[SERVICE] Mensaje: {message[:60]}...", file=sys.stderr)

            # LOG: Mensaje del usuario
            if self.chat_logger:
                self.chat_logger.log_user_message(message)

            # Get the agent
            print(f"[SERVICE] Creando agente...", file=sys.stderr)
            agent = self._get_agent()

            if agent is None:
                raise ValueError("El agente no pudo ser inicializado correctamente")

            if not hasattr(agent, 'query') or not callable(agent.query):
                raise AttributeError(f"El agente no tiene un método 'query' válido. Tipo: {type(agent)}")

            print(f"[SERVICE] Agente creado correctamente", file=sys.stderr)

            # Set API key in environment for this request
            if self.provider != 'ollama':
                env_var_map = {
                    'gemini': 'GOOGLE_API_KEY',
                    'openai': 'OPENAI_API_KEY',
                    'nvidia': 'NVIDIA_API_KEY'
                }
                env_var = env_var_map.get(self.provider, 'GOOGLE_API_KEY')
                os.environ[env_var] = self.api_key

            # Prepare conversation history for the agent
            formatted_history = []
            if conversation_history and len(conversation_history) > 0:
                max_history = int(os.getenv('MAX_CONVERSATION_HISTORY', '10'))
                print(f"[SERVICE] Añadiendo historial de conversación ({len(conversation_history)} mensajes, límite: {max_history})...", file=sys.stderr)

                recent_history = conversation_history[-max_history:] if len(conversation_history) > max_history else conversation_history
                for msg in recent_history:
                    formatted_history.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })

            # LOG: Request al LLM
            if self.chat_logger:
                model = self.ollama_model if self.provider == 'ollama' else self.openai_model
                messages = formatted_history + [{'role': 'user', 'content': message}]
                self.chat_logger.log_llm_request(
                    provider=self.provider,
                    model=model,
                    messages=messages,
                    tools=None
                )

            # Execute query through the agent
            print(f"[SERVICE] Ejecutando query en el agente...", file=sys.stderr)
            result = agent.query(message, conversation_history=formatted_history)
            print(f"[SERVICE] Query ejecutado correctamente", file=sys.stderr)

            # LOG: Respuesta del LLM
            if self.chat_logger:
                self.chat_logger.log_llm_response(result)

            # Extract response content
            response_content = result.get('answer', 'No se pudo generar una respuesta.')

            # ========================================================================
            # REVIEW AND IMPROVEMENT LOOP
            # ========================================================================
            from apps.chat.response_reviewer import ResponseReviewer

            max_review_loops = getattr(self.user, 'max_review_loops', 3)
            print(f"[SERVICE] Iniciando sistema de revisión (max_loops: {max_review_loops})...", file=sys.stderr)

            reviewer = ResponseReviewer(agent.llm, tool_registry=agent.tool_registry, chat_logger=self.chat_logger)

            review_history = []
            current_loop = 0
            improvement_applied = False
            all_review_scores = []

            while current_loop < max_review_loops:
                current_loop += 1
                print(f"[SERVICE] === REVIEW LOOP {current_loop}/{max_review_loops} ===", file=sys.stderr)

                if self.chat_logger:
                    self.chat_logger.log_review_start(current_loop, max_review_loops)

                review_metadata_input = {
                    'documents_used': result.get('documents', []),
                    'tools_executed': result.get('tool_results', []),
                    'route': result.get('route', 'unknown')
                }

                review_result = reviewer.review_response(
                    user_question=message,
                    conversation_history=formatted_history,
                    initial_response=response_content,
                    metadata=review_metadata_input,
                    current_loop_num=current_loop,
                    max_loops=max_review_loops
                )

                all_review_scores.append(review_result['score'])
                review_history.append({
                    'loop': current_loop,
                    'score': review_result['score'],
                    'feedback': review_result.get('feedback', ''),
                    'issues': review_result['issues'],
                    'suggestions': review_result['suggestions'],
                    'tool_suggestions': review_result.get('tool_suggestions', []),
                    'continue_improving': review_result.get('continue_improving', True)
                })

                print(f"[SERVICE] Loop {current_loop} - Review completada (score: {review_result['score']}/100)", file=sys.stderr)

                # Exit conditions
                if current_loop >= max_review_loops:
                    reason = f"Límite de loops alcanzado ({max_review_loops})"
                    print(f"[SERVICE] {reason}. Retornando respuesta final.", file=sys.stderr)
                    if self.chat_logger:
                        self.chat_logger.log_review_end(current_loop, "COMPLETED", reason)
                    break

                if current_loop == 1:
                    print(f"[SERVICE] Loop 1 obligatorio - Ejecutando mejora...", file=sys.stderr)
                    improvement_applied = True
                elif current_loop >= 2:
                    if not review_result.get('continue_improving', True):
                        reason = f"Revisor decidió NO continuar mejorando"
                        print(f"[SERVICE] {reason}", file=sys.stderr)
                        if self.chat_logger:
                            self.chat_logger.log_review_end(current_loop, "APPROVED", reason)
                        break
                    else:
                        print(f"[SERVICE] Revisor decidió continuar mejorando...", file=sys.stderr)
                        improvement_applied = True

                # Build improvement prompt
                issues_list = '\n'.join([f"- {issue}" for issue in review_result['issues']])
                suggestions_list = '\n'.join([f"- {suggestion}" for suggestion in review_result['suggestions']])

                tool_suggestions_section = ""
                if review_result.get('tool_suggestions'):
                    tool_suggestions_section = "\n**Herramientas recomendadas:**\n"
                    for ts in review_result['tool_suggestions']:
                        tool_suggestions_section += f"- {ts['tool']}: {ts['reason']}\n"

                has_tool_suggestions = bool(review_result.get('tool_suggestions'))

                if has_tool_suggestions:
                    tools_instruction = """**IMPORTANTE - USO DE HERRAMIENTAS:**
- DEBES usar las herramientas sugeridas para completar la información"""
                else:
                    tools_instruction = """**IMPORTANTE - REFORMULACIÓN:**
- NO uses herramientas para esta mejora
- SOLO reformula y mejora la respuesta actual"""

                improvement_prompt = f"""Tu respuesta anterior fue revisada (Loop {current_loop}/{max_review_loops}). Vamos a mejorarla.

**Tu respuesta actual:**
{response_content}

**Problemas detectados:**
{issues_list if issues_list else '- Ningún problema grave detectado'}

**Sugerencias de mejora:**
{suggestions_list if suggestions_list else '- Mantener el buen formato actual'}
{tool_suggestions_section}
{tools_instruction}

**Pregunta original del usuario:**
{message}

Genera tu respuesta mejorada:"""

                if self.chat_logger:
                    self.chat_logger.log_improvement_prompt(
                        prompt=improvement_prompt,
                        loop_num=current_loop,
                        review_result=review_result
                    )

                improvement_history = formatted_history + [
                    {'role': 'user', 'content': message},
                    {'role': 'assistant', 'content': response_content}
                ]

                print(f"[SERVICE] Ejecutando query de mejora (loop {current_loop})...", file=sys.stderr)
                improved_result = agent.query(
                    improvement_prompt,
                    conversation_history=improvement_history
                )

                previous_response_length = len(response_content)
                response_content = improved_result.get('answer', response_content)
                new_response_length = len(response_content)

                print(f"[SERVICE] Loop {current_loop} - Respuesta mejorada: {previous_response_length} → {new_response_length} caracteres", file=sys.stderr)

                if self.chat_logger:
                    self.chat_logger.log_review_end(
                        current_loop,
                        "IMPROVED",
                        f"Mejora aplicada: {previous_response_length} → {new_response_length} caracteres"
                    )

                # Merge results
                result['tools_used'] = list(set(result.get('tools_used', []) + improved_result.get('tools_used', [])))
                result['iterations'] = result.get('iterations', 0) + improved_result.get('iterations', 0)

            # Build review tracking
            last_review = review_history[-1] if review_history else {}
            continue_improving = last_review.get('continue_improving', False)
            review_status = 'NEEDS_IMPROVEMENT' if continue_improving else 'APPROVED'

            review_tracking = {
                'review_performed': True,
                'max_loops': max_review_loops,
                'loops_executed': current_loop,
                'improvement_applied': improvement_applied,
                'all_scores': all_review_scores,
                'final_score': all_review_scores[-1] if all_review_scores else 100,
                'review_history': review_history,
                'review_status': review_status,
                'review_score': last_review.get('score', 100),
                'review_issues': last_review.get('issues', []),
                'review_suggestions': last_review.get('suggestions', []),
                'continue_improving': continue_improving
            }

            print(f"[SERVICE] Review completado: {current_loop} loops ejecutados, scores: {all_review_scores}", file=sys.stderr)

            # Calculate token usage and cost
            from apps.core.token_pricing import calculate_chat_cost

            cost_data = calculate_chat_cost(
                input_text=message,
                output_text=response_content,
                provider=self.provider
            )

            # Build metadata response
            metadata = {
                'provider': self.provider,
                'route': result.get('route', 'unknown'),
                'documents_used': [],
                'iterations': result.get('iterations', 0),
                'tools_used': result.get('tools_used', []),
                'tools_failed': result.get('tools_failed', []),
                'input_tokens': cost_data['input_tokens'],
                'output_tokens': cost_data['output_tokens'],
                'total_tokens': cost_data['total_tokens'],
                'cost_eur': cost_data['total_cost_eur'],
                'review': review_tracking
            }

            print(f"[SERVICE] Respuesta procesada: {len(response_content)} caracteres", file=sys.stderr)
            print(f"[SERVICE] Tokens totales: {cost_data['total_tokens']}", file=sys.stderr)
            print(f"[SERVICE] Costo: €{cost_data['total_cost_eur']:.4f}", file=sys.stderr)
            print(f"[SERVICE] Review - Final Score: {review_tracking['final_score']}/100", file=sys.stderr)

            # LOG: Mensaje final del asistente
            if self.chat_logger:
                self.chat_logger.log_assistant_message(response_content, metadata=metadata)

            return {
                'content': response_content,
                'metadata': metadata
            }

        except ValueError as e:
            return {
                'content': f'Error de configuración: {str(e)}',
                'metadata': {
                    'error': 'CONFIGURATION_ERROR',
                    'route': 'error',
                    'documents_used': [],
                    'iterations': 0
                }
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'content': f'Lo siento, ocurrió un error al procesar tu mensaje: {error_msg}',
                'metadata': {
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'route': 'error',
                    'documents_used': [],
                    'iterations': 0
                }
            }

    def reset_agent(self):
        """
        Reset the cached agent instance
        """
        self._agent = None
