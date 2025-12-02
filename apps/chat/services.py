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
    """Service to interact with the Agent_IA RAG system"""

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

        # Obtener contexto de empresa si existe
        self.company_context = self._get_company_context()

        # DEBUG: Imprimir contexto de empresa
        if self.company_context:
            print(f"[SERVICE] ✓ Contexto de empresa cargado: {len(self.company_context)} caracteres", file=sys.stderr)
            print(f"[SERVICE] Contexto: {self.company_context[:200]}...", file=sys.stderr)
        else:
            print(f"[SERVICE] ⚠️ NO hay contexto de empresa", file=sys.stderr)

        # Obtener resumen de licitaciones disponibles
        self.tenders_summary = self._get_tenders_summary()

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

        # Always use Function Calling Agent (modern implementation)
        return self._create_function_calling_agent()

    def _create_function_calling_agent(self):
        """
        Create and return a FunctionCallingAgent instance
        """
        try:
            from agent_ia_core.agent_function_calling import FunctionCallingAgent
            from agent_ia_core.indexing.retriever import create_retriever

            print(f"[SERVICE] Creando FunctionCallingAgent...", file=sys.stderr)
            print(f"[SERVICE] Proveedor: {self.provider}", file=sys.stderr)

            # Verificar Ollama si es necesario
            if self.provider == 'ollama':
                self._verify_ollama_availability()

            # Crear retriever con el modelo de embeddings correcto según el provider
            if self.provider == 'ollama':
                embedding_model = self.ollama_embedding_model
            elif self.provider == 'openai':
                embedding_model = self.openai_embedding_model
            else:
                embedding_model = None  # Gemini u otros providers

            retriever = create_retriever(
                k=6,
                provider=self.provider,
                api_key=None if self.provider == 'ollama' else self.api_key,
                embedding_model=embedding_model
            )

            # Determinar el modelo según el proveedor
            if self.provider == 'ollama':
                model = self.ollama_model
            elif self.provider == 'openai':
                model = self.openai_model  # Usar modelo seleccionado por el usuario
            elif self.provider == 'google':
                model = 'gemini-2.0-flash-exp'  # Modelo por defecto de Gemini
            else:
                model = self.ollama_model  # Fallback

            # Crear agente con usuario (para tools de contexto)
            self._agent = FunctionCallingAgent(
                llm_provider=self.provider,
                llm_model=model,
                llm_api_key=None if self.provider == 'ollama' else self.api_key,
                retriever=retriever,
                db_session=None,  # Usa conexión Django default
                user=self.user,  # Pasar usuario para tools de contexto
                max_iterations=15,  # Aumentado de 5 a 15
                temperature=0.3,
                company_context=self.company_context,  # Mantener por compatibilidad (deprecated)
                tenders_summary=self.tenders_summary,   # Mantener por compatibilidad (deprecated)
                chat_logger=self.chat_logger  # Pasar logger para logging detallado
            )

            print(f"[SERVICE] ✓ FunctionCallingAgent creado con {len(self._agent.tool_registry.tools)} tools", file=sys.stderr)
            if self.user:
                print(f"[SERVICE] ✓ Tools de contexto disponibles (get_company_info, get_tenders_summary)", file=sys.stderr)
            if self.company_context:
                print(f"[SERVICE] ✓ Contexto de empresa cargado (deprecated - ahora usa get_company_info tool)", file=sys.stderr)
            if self.tenders_summary:
                print(f"[SERVICE] ✓ Resumen de licitaciones cargado (deprecated - ahora usa get_tenders_summary tool)", file=sys.stderr)
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

    def _get_company_context(self) -> str:
        """
        Obtiene el contexto de la empresa del usuario.

        Returns:
            String con el contexto formateado de la empresa, o vacío si no existe perfil
        """
        try:
            from apps.company.models import CompanyProfile

            # Buscar perfil de empresa
            profile = CompanyProfile.objects.filter(user=self.user).first()

            if not profile:
                return ""

            # Usar el método get_chat_context() del modelo
            return profile.get_chat_context()

        except Exception as e:
            # Si hay error, retornar vacío para no bloquear el chat
            print(f"[SERVICE] Error obteniendo contexto de empresa: {e}", file=sys.stderr)
            return ""

    def _get_tenders_summary(self) -> str:
        """
        Obtiene un resumen de todas las licitaciones disponibles (parsed_summary).
        Incluye solo campos esenciales para resumen inicial.

        Campos incluidos:
        - ojs_notice_id, title, buyer_name, cpv_main (REQUIRED)
        - description, cpv_additional, budget_eur, tender_deadline_date,
          publication_date, contract_type, nuts_regions, procedure_type (OPTIONAL)

        Returns:
            String con resumen formateado de licitaciones, o vacío si no hay
        """
        try:
            from apps.tenders.models import Tender
            import json

            # Obtener TODAS las licitaciones que tienen parsed_summary (sin límite)
            tenders = Tender.objects.exclude(parsed_summary={}).exclude(parsed_summary__isnull=True).order_by('-publication_date')

            if not tenders.exists():
                return ""

            total_count = tenders.count()
            summary_parts = [
                "LICITACIONES DISPONIBLES EN LA BASE DE DATOS:",
                f"Total: {total_count} licitaciones",
                ""
            ]

            for idx, tender in enumerate(tenders, 1):
                parsed = tender.parsed_summary
                required = parsed.get('REQUIRED', {})
                optional = parsed.get('OPTIONAL', {})

                # Extraer solo campos esenciales
                tender_data = {
                    'ojs_notice_id': required.get('ojs_notice_id'),
                    'title': required.get('title'),
                    'buyer_name': required.get('buyer_name'),
                    'cpv_main': required.get('cpv_main'),
                    'description': optional.get('description'),  # Completa
                    'cpv_additional': optional.get('cpv_additional'),
                    'budget_eur': optional.get('budget_eur'),
                    'tender_deadline_date': optional.get('tender_deadline_date'),
                    'publication_date': required.get('publication_date'),
                    'contract_type': optional.get('contract_type'),
                    'nuts_regions': optional.get('nuts_regions'),
                    'procedure_type': optional.get('procedure_type')
                }

                # Convertir a JSON formateado para legibilidad
                tender_json = json.dumps(tender_data, ensure_ascii=False, indent=2)

                summary_parts.append(f"[{idx}] Licitación {required.get('ojs_notice_id', 'N/A')}")
                summary_parts.append(tender_json)
                summary_parts.append('')  # Línea en blanco entre licitaciones

            return '\n'.join(summary_parts)

        except Exception as e:
            # Si hay error, retornar vacío para no bloquear el chat
            print(f"[SERVICE] Error obteniendo resumen de licitaciones: {e}", file=sys.stderr)
            return ""


    def _enrich_with_company_context(self, message: str) -> str:
        """
        Enrich user message with company profile context for better recommendations

        Args:
            message: Original user message

        Returns:
            Enriched message with company context prepended
        """
        try:
            from apps.company.models import CompanyProfile

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
                                  Limited by MAX_CONVERSATION_HISTORY env var (default: 10) to avoid token overflow

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

            # LOG: Mensaje del usuario
            if self.chat_logger:
                self.chat_logger.log_user_message(message)

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

            # IMPORTANTE: Para routing efectivo, pasamos SOLO el mensaje actual (sin historial)
            # Esto permite que el LLM clasifique cada pregunta de forma independiente
            # El historial se añadirá después en el nodo de respuesta (answer_node)

            # Enrich message with company profile context if asking for recommendations
            enriched_message = message
            recommendation_keywords = ['adecua', 'recomend', 'mejor', 'apropiada', 'conveniente', 'ideal', 'mi empresa']
            if any(keyword in message.lower() for keyword in recommendation_keywords):
                print(f"[SERVICE] Enriqueciendo mensaje con contexto de empresa...", file=sys.stderr)
                enriched_message = self._enrich_with_company_context(message)

            # Prepare conversation history for the agent
            formatted_history = []
            if conversation_history and len(conversation_history) > 0:
                # Get max history from settings
                max_history = int(os.getenv('MAX_CONVERSATION_HISTORY', '10'))
                print(f"[SERVICE] Añadiendo historial de conversación ({len(conversation_history)} mensajes, límite: {max_history})...", file=sys.stderr)

                # Format history (limit to avoid token overflow)
                recent_history = conversation_history[-max_history:] if len(conversation_history) > max_history else conversation_history
                for msg in recent_history:
                    formatted_history.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })

            # Execute query through the agent
            # Pasamos el mensaje actual PURO (sin historial) para routing correcto
            # El historial se pasa por separado
            print(f"[SERVICE] Ejecutando query en el agente...", file=sys.stderr)
            print(f"[SERVICE] Mensaje puro (para routing): {enriched_message[:60]}...", file=sys.stderr)
            print(f"[SERVICE] Historial: {len(formatted_history)} mensajes", file=sys.stderr)

            # LOG: Request al LLM (antes de ejecutar)
            if self.chat_logger:
                model = self.ollama_model if self.provider == 'ollama' else self.openai_model
                # Construir mensajes que se enviarán (aproximación)
                messages = formatted_history + [{'role': 'user', 'content': enriched_message}]
                self.chat_logger.log_llm_request(
                    provider=self.provider,
                    model=model,
                    messages=messages,
                    tools=None  # Las tools se registran dentro del agente
                )

            result = agent.query(enriched_message, conversation_history=formatted_history)
            print(f"[SERVICE] ✓ Query ejecutado correctamente", file=sys.stderr)

            # LOG: Respuesta del LLM
            if self.chat_logger:
                self.chat_logger.log_llm_response(result)

            # Extract response content
            response_content = result.get('answer', 'No se pudo generar una respuesta.')

            # ========================================================================
            # REVIEW AND IMPROVEMENT LOOP WITH CONFIGURABLE MAX LOOPS
            # ========================================================================
            from apps.chat.response_reviewer import ResponseReviewer

            # Get max_review_loops from user configuration (default: 3)
            max_review_loops = getattr(self.user, 'max_review_loops', 3)
            print(f"[SERVICE] Iniciando sistema de revisión (max_loops: {max_review_loops})...", file=sys.stderr)

            # Create reviewer with same LLM as agent AND pass chat_logger
            reviewer = ResponseReviewer(agent.llm, chat_logger=self.chat_logger)

            # Initialize review tracking
            review_history = []  # Historial de todas las revisiones
            current_loop = 0
            improvement_applied = False
            all_review_scores = []

            # REVIEW-IMPROVE LOOP
            while current_loop < max_review_loops:
                current_loop += 1
                print(f"[SERVICE] === REVIEW LOOP {current_loop}/{max_review_loops} ===", file=sys.stderr)

                # Log inicio del loop de revisión
                self.chat_logger.log_review_start(current_loop, max_review_loops)

                # Build metadata for reviewer (con tools ejecutadas completas)
                review_metadata_input = {
                    'documents_used': result.get('documents', []),
                    'tools_executed': result.get('tool_results', []),  # Información COMPLETA de tools
                    'route': result.get('route', 'unknown')
                }

                # Review current response
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
                print(f"[SERVICE] Revisor dice continue_improving: {review_result.get('continue_improving', True)}", file=sys.stderr)

                # ========================================================================
                # DECISIONES DE SALIDA DEL LOOP
                # ========================================================================

                # 1. Límite de loops alcanzado
                if current_loop >= max_review_loops:
                    reason = f"Límite de loops alcanzado ({max_review_loops})"
                    print(f"[SERVICE] {reason}. Retornando respuesta final.", file=sys.stderr)
                    self.chat_logger.log_review_end(current_loop, "COMPLETED", reason)
                    break

                # 2. Loop 1 SIEMPRE ejecuta mejora (obligatorio)
                if current_loop == 1:
                    print(f"[SERVICE] Loop 1 obligatorio - Ejecutando mejora...", file=sys.stderr)
                    improvement_applied = True
                    # No hacer break, continuar a ejecutar mejora

                # 3. Loop 2+: Revisor decide si continuar
                elif current_loop >= 2:
                    if not review_result.get('continue_improving', True):
                        reason = f"Revisor decidió NO continuar mejorando (respuesta suficientemente buena)"
                        print(f"[SERVICE] {reason}", file=sys.stderr)
                        self.chat_logger.log_review_end(current_loop, "APPROVED", reason)
                        break
                    else:
                        print(f"[SERVICE] Revisor decidió continuar mejorando. Ejecutando Loop {current_loop} mejora...", file=sys.stderr)
                        improvement_applied = True

                # Build lists for prompt
                issues_list = '\n'.join([f"- {issue}" for issue in review_result['issues']])
                suggestions_list = '\n'.join([f"- {suggestion}" for suggestion in review_result['suggestions']])

                # Build tool suggestions section
                tool_suggestions_section = ""
                if review_result.get('tool_suggestions'):
                    tool_suggestions_section = "\n**Herramientas recomendadas por el revisor:**\n"
                    for ts in review_result['tool_suggestions']:
                        tool_suggestions_section += f"- {ts['tool']}: {ts['reason']}\n"
                        tool_suggestions_section += f"  Parámetros sugeridos: {ts['params']}\n"

                # Build param validation section
                param_validation_section = ""
                if review_result.get('param_validation'):
                    param_validation_section = "\n**Validación de parámetros de tools ya ejecutadas:**\n"
                    for pv in review_result['param_validation']:
                        param_validation_section += f"- {pv['tool']} - parámetro '{pv['param']}': {pv['issue']}\n"
                        param_validation_section += f"  Valor sugerido: {pv['suggested']}\n"

                # Build improvement prompt with feedback
                if review_result['feedback']:
                    feedback_section = f"""**Feedback del revisor:**
{review_result['feedback']}"""
                else:
                    feedback_section = "**Nota del revisor:** La respuesta está bien estructurada, pero podemos mejorarla."

                improvement_prompt = f"""Tu respuesta anterior fue revisada (Loop {current_loop}/{max_review_loops}). Vamos a mejorarla.

**Tu respuesta actual:**
{response_content}

**Problemas detectados:**
{issues_list if issues_list else '- Ningún problema grave detectado'}

**Sugerencias:**
{suggestions_list if suggestions_list else '- Mantener el buen formato actual'}
{tool_suggestions_section}{param_validation_section}
{feedback_section}

**Tu tarea:**
Genera una respuesta MEJORADA que sea aún más completa y útil.

**IMPORTANTE:**
- Usa herramientas (tools) si necesitas buscar más información
- El revisor ha sugerido herramientas específicas arriba - ÚSALAS si son relevantes
- Si faltan datos específicos (presupuestos, plazos, etc.), búscalos con las tools apropiadas
- Si el formato es incorrecto, corrígelo (usa ## para licitaciones múltiples, NO listas numeradas)
- Si falta análisis, justifica tus recomendaciones con datos concretos
- Si ya está bien, puedes añadir más detalles útiles o mejorar la presentación

**Pregunta original del usuario:**
{message}

Genera tu respuesta mejorada:"""

                # Log del improvement prompt
                self.chat_logger.log_improvement_prompt(
                    prompt=improvement_prompt,
                    loop_num=current_loop,
                    review_result=review_result
                )

                # Execute improvement query
                # Añadir respuesta actual al historial para contexto
                improvement_history = formatted_history + [
                    {'role': 'user', 'content': message},
                    {'role': 'assistant', 'content': response_content}
                ]

                print(f"[SERVICE] Ejecutando query de mejora (loop {current_loop})...", file=sys.stderr)
                improved_result = agent.query(
                    improvement_prompt,
                    conversation_history=improvement_history
                )

                # Update response with improved version
                previous_response_length = len(response_content)
                response_content = improved_result.get('answer', response_content)
                new_response_length = len(response_content)

                print(f"[SERVICE] ✓ Loop {current_loop} - Respuesta mejorada: {previous_response_length} → {new_response_length} caracteres", file=sys.stderr)

                # Log fin del loop con mejora aplicada
                self.chat_logger.log_review_end(
                    current_loop,
                    "IMPROVED",
                    f"Mejora aplicada: {previous_response_length} → {new_response_length} caracteres"
                )

                # Merge documents (avoid duplicates)
                existing_doc_ids = {doc.get('ojs_notice_id') for doc in result.get('documents', [])}
                new_docs = [doc for doc in improved_result.get('documents', [])
                           if doc.get('ojs_notice_id') not in existing_doc_ids]
                result['documents'] = result.get('documents', []) + new_docs

                # Merge tool results (información completa de tools ejecutadas)
                result['tool_results'] = result.get('tool_results', []) + improved_result.get('tool_results', [])

                # Merge tools used (nombres únicos para compatibilidad)
                result['tools_used'] = list(set(result.get('tools_used', []) + improved_result.get('tools_used', [])))

                # Update iterations count
                result['iterations'] = result.get('iterations', 0) + improved_result.get('iterations', 0)

            # Save comprehensive review metadata for tracking
            # Determinar status basado en continue_improving de la última revisión
            last_continue_improving = review_history[-1].get('continue_improving', False) if review_history else False
            derived_status = 'NEEDS_IMPROVEMENT' if last_continue_improving else 'APPROVED'

            review_tracking = {
                'review_performed': True,
                'max_loops': max_review_loops,
                'loops_executed': current_loop,
                'improvement_applied': improvement_applied,
                'all_scores': all_review_scores,
                'final_score': all_review_scores[-1] if all_review_scores else 100,
                'review_history': review_history,
                # Mantener compatibilidad con código anterior (usar última revisión)
                'review_status': derived_status,  # Derivado de continue_improving
                'review_score': review_history[-1]['score'] if review_history else 100,
                'review_issues': review_history[-1]['issues'] if review_history else [],
                'review_suggestions': review_history[-1]['suggestions'] if review_history else [],
                'continue_improving': last_continue_improving  # Añadir para transparencia
            }

            print(f"[SERVICE] Review completado: {current_loop} loops ejecutados, scores: {all_review_scores}", file=sys.stderr)
            # ========================================================================
            # END REVIEW LOOP
            # ========================================================================

            # Format document metadata for frontend
            from apps.tenders.models import Tender
            documents_used = []
            for doc in result.get('documents', []):
                tender_id = doc.get('ojs_notice_id', 'unknown')

                # Obtener título desde la BD para mostrarlo como enlace clickeable
                try:
                    tender = Tender.objects.get(ojs_notice_id=tender_id)
                    title = tender.title
                except Tender.DoesNotExist:
                    title = f'Licitación {tender_id}'

                documents_used.append({
                    'id': tender_id,
                    'title': title,  # Título para enlace clickeable en chat
                    'section': doc.get('section', 'unknown'),
                    'content_preview': doc.get('content', '')[:150] + '...'
                })

            # Calculate token usage and cost
            from apps.core.token_pricing import calculate_chat_cost

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
                'provider': self.provider,  # Añadir provider para distinguir Ollama
                'route': result.get('route', 'unknown'),
                'documents_used': documents_used,
                'verified_fields': result.get('verified_fields', []),
                'iterations': result.get('iterations', 0),
                'num_documents': len(documents_used),
                'tools_used': result.get('tools_used', []),  # Añadir tools usadas
                'tools_failed': result.get('tools_failed', []),  # Añadir tools fallidas con info de reintentos
                # Token and cost tracking
                'input_tokens': cost_data['input_tokens'],
                'output_tokens': cost_data['output_tokens'],
                'total_tokens': cost_data['total_tokens'],
                'cost_eur': cost_data['total_cost_eur'],
                # Review tracking (from LLM reviewer)
                'review': review_tracking
            }

            # Log final del proceso
            print(f"[SERVICE] ✓ Respuesta procesada: {len(response_content)} caracteres", file=sys.stderr)
            print(f"[SERVICE] Documentos recuperados: {len(documents_used)}", file=sys.stderr)
            tools_used = result.get('tools_used', [])
            if tools_used:
                print(f"[SERVICE] Herramientas usadas ({len(tools_used)}): {' → '.join(tools_used)}", file=sys.stderr)
            print(f"[SERVICE] Tokens totales: {cost_data['total_tokens']} (in: {cost_data['input_tokens']}, out: {cost_data['output_tokens']})", file=sys.stderr)
            print(f"[SERVICE] Costo: €{cost_data['total_cost_eur']:.4f}", file=sys.stderr)
            # Review metrics (enhanced with loop information)
            print(f"[SERVICE] Review - Loops: {review_tracking['loops_executed']}/{review_tracking['max_loops']}", file=sys.stderr)
            print(f"[SERVICE] Review - Final Score: {review_tracking['final_score']}/100 (all scores: {review_tracking['all_scores']})", file=sys.stderr)
            print(f"[SERVICE] Review - Status: {review_tracking['review_status']}", file=sys.stderr)
            if review_tracking['improvement_applied']:
                print(f"[SERVICE] Review - Mejoras aplicadas en {review_tracking['loops_executed']} loops", file=sys.stderr)
                if review_tracking['review_issues']:
                    print(f"[SERVICE] Review - Issues detectados: {len(review_tracking['review_issues'])}", file=sys.stderr)
            else:
                print(f"[SERVICE] Review - Sin mejoras (score suficientemente alto o límite alcanzado)", file=sys.stderr)
            print(f"", file=sys.stderr)  # Línea en blanco final

            # LOG: Mensaje final del asistente con metadata
            if self.chat_logger:
                self.chat_logger.log_assistant_message(response_content, metadata=metadata)

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
