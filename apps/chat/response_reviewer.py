# -*- coding: utf-8 -*-
"""
LLM Revisor de Respuestas - Sistema de Auto-mejora
Revisa formato y contenido de las respuestas del agente principal.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ResponseReviewer:
    """
    Revisor inteligente que analiza respuestas del agente principal.

    Revisa:
    - Formato: Markdown correcto, estructura clara
    - Contenido: Completitud, precisión, relevancia
    - Coherencia: Responde la pregunta, usa documentos correctamente
    """

    def __init__(self, llm, chat_logger: Optional[Any] = None):
        """
        Inicializa el revisor con un LLM.

        Args:
            llm: Instancia del LLM (ChatOllama, ChatOpenAI, ChatGemini, etc.)
            chat_logger: Instancia de ChatLogger para logging detallado (opcional)
        """
        self.llm = llm
        self.chat_logger = chat_logger

    def review_response(
        self,
        user_question: str,
        conversation_history: List[Dict[str, str]],
        initial_response: str,
        metadata: Dict[str, Any],
        current_loop_num: int = 1,
        max_loops: int = 3
    ) -> Dict[str, Any]:
        """
        Revisa una respuesta del agente principal.

        Args:
            user_question: Pregunta original del usuario
            conversation_history: Historial de la conversación
            initial_response: Respuesta inicial generada por el agente
            metadata: Metadatos (documentos usados, tools ejecutadas completas, etc.)
            current_loop_num: Número de loop actual (para contexto del revisor)
            max_loops: Máximo de loops configurados (para contexto del revisor)

        Returns:
            Dict con formato:
            {
                'feedback': str,  # SIEMPRE presente
                'score': float (0-100),  # Solo informativo
                'issues': List[str],  # Problemas detectados
                'suggestions': List[str],  # Sugerencias de mejora
                'tool_suggestions': List[Dict],  # Tools que debería llamar
                'param_validation': List[Dict],  # Validación de parámetros de tools ya ejecutadas
                'continue_improving': bool  # Si debe continuar mejorando (Loop 2+)
            }
        """
        logger.info("[REVIEWER] Iniciando revisión de respuesta...")

        try:
            # Construir prompt de revisión
            review_prompt = self._build_review_prompt(
                user_question=user_question,
                conversation_history=conversation_history,
                initial_response=initial_response,
                metadata=metadata,
                current_loop_num=current_loop_num,
                max_loops=max_loops
            )

            # Log del prompt del revisor (si chat_logger disponible)
            if self.chat_logger:
                self.chat_logger.log_reviewer_prompt(
                    prompt=review_prompt,
                    user_question=user_question,
                    conversation_history=conversation_history,
                    metadata=metadata
                )

            # Llamar al LLM revisor
            logger.info("[REVIEWER] Llamando al LLM revisor...")

            # Log de la request al LLM revisor (si chat_logger disponible)
            if self.chat_logger:
                # Extraer provider y model del LLM
                model_name = getattr(self.llm, 'model_name', getattr(self.llm, 'model', 'unknown'))
                provider = self.llm.__class__.__name__.replace('Chat', '').lower()

                self.chat_logger.log_llm_request(
                    provider=provider,
                    model=model_name,
                    messages=[{'role': 'user', 'content': review_prompt}],
                    tools=None,
                    context="REVIEWER"
                )

            review_result = self.llm.invoke(review_prompt)

            # Log de la response del LLM revisor (si chat_logger disponible)
            if self.chat_logger:
                self.chat_logger.log_llm_response(review_result, context="REVIEWER")

            # Parsear respuesta del revisor
            parsed_review = self._parse_review_response(review_result.content)

            # Log de la respuesta parseada del revisor (si chat_logger disponible)
            if self.chat_logger:
                self.chat_logger.log_reviewer_response(
                    raw_response=review_result.content,
                    parsed_result=parsed_review
                )

            logger.info(
                f"[REVIEWER] Revisión completada "
                f"(score: {parsed_review['score']}/100, continue_improving: {parsed_review.get('continue_improving', True)})"
            )

            return parsed_review

        except Exception as e:
            logger.error(f"[REVIEWER] Error en revisión: {e}", exc_info=True)
            # Fallback: retornar valores por defecto si hay error
            return {
                'feedback': 'Error en revisión, usando valores por defecto',
                'score': 100,
                'issues': [],
                'suggestions': [],
                'tool_suggestions': [],
                'param_validation': [],
                'continue_improving': False,  # No continuar si hay error
                'error': str(e)
            }

    def _build_review_prompt(
        self,
        user_question: str,
        conversation_history: List[Dict[str, str]],
        initial_response: str,
        metadata: Dict[str, Any],
        current_loop_num: int,
        max_loops: int
    ) -> str:
        """Construye el prompt de revisión para el LLM revisor."""

        # Formatear historial
        history_text = self._format_conversation_history(conversation_history)

        # Información de documentos
        docs_info = ""
        if metadata.get('documents_used'):
            docs_info = f"\n\n**Documentos consultados:** {len(metadata['documents_used'])} documentos"
            docs_ids = [doc.get('ojs_notice_id', 'unknown') for doc in metadata['documents_used'][:5]]
            docs_info += f"\nIDs: {', '.join(docs_ids)}"

        # Información de tools ejecutadas (con parámetros y resultados)
        tools_info = ""
        tools_executed = metadata.get('tools_executed', [])
        if tools_executed:
            tools_info = f"\n\n**Herramientas ejecutadas:** {len(tools_executed)} tools\n"
            for idx, tool_exec in enumerate(tools_executed[:5], 1):  # Mostrar max 5
                tool_name = tool_exec.get('tool', 'unknown')
                tool_args = tool_exec.get('arguments', {})
                tool_result = tool_exec.get('result', {})
                success = tool_result.get('success', False) if isinstance(tool_result, dict) else True
                status_emoji = "✓" if success else "✗"

                tools_info += f"{idx}. {status_emoji} {tool_name}"
                if tool_args:
                    args_str = str(tool_args)[:100] + "..." if len(str(tool_args)) > 100 else str(tool_args)
                    tools_info += f" (params: {args_str})"
                tools_info += "\n"

        # Contexto del loop para el revisor
        loop_context = ""
        if current_loop_num == 1:
            loop_context = f"\n**CONTEXTO:** Este es el Loop 1/{max_loops} (obligatorio). El agente SIEMPRE ejecutará una mejora después de esta revisión."
        else:
            loop_context = f"\n**CONTEXTO:** Este es el Loop {current_loop_num}/{max_loops}. Tu decisión de CONTINUE_IMPROVING determinará si se ejecuta otra iteración."

        prompt = f"""Eres un **revisor experto de respuestas de chatbot sobre licitaciones públicas**.

Tu tarea es revisar la respuesta generada por el agente principal.
{loop_context}

**CONTEXTO DE LA CONVERSACIÓN:**

Historial:
{history_text}

Pregunta actual del usuario:
"{user_question}"
{docs_info}{tools_info}

---

**RESPUESTA GENERADA POR EL AGENTE:**

{initial_response}

---

**TU TAREA:**

Analiza la respuesta y evalúa:

1. **FORMATO (30 puntos):**
   - ¿Usa Markdown correctamente?
   - Si hay múltiples licitaciones, ¿usa ## para cada una? (NO listas numeradas 1. 2. 3.)
   - ¿Está bien estructurado y es legible?

2. **CONTENIDO (40 puntos):**
   - ¿Responde completamente a la pregunta del usuario?
   - ¿Incluye todos los datos relevantes (IDs, presupuestos, plazos)?
   - ¿Falta información importante que debería estar?

3. **ANÁLISIS (30 puntos):**
   - Si el usuario pidió recomendaciones, ¿justifica con datos?
   - ¿Usa los documentos consultados correctamente?
   - ¿Es útil y profesional?

**INSTRUCCIONES DE RESPUESTA:**

Responde EXACTAMENTE en este formato:

```
SCORE: [0-100]
(El score es SOLO informativo, NO afecta decisiones del sistema)

ISSUES:
- [Problema 1 si existe]
- [Problema 2 si existe]
(Si no hay problemas, escribe: Ninguno)

SUGGESTIONS:
- [Sugerencia 1 si existe]
- [Sugerencia 2 si existe]
(Si no hay sugerencias, escribe: Ninguna)

TOOL_SUGGESTIONS:
- tool: [nombre_tool], params: {{parametros}}, reason: [razón por la que debe llamarla]
- tool: [nombre_tool], params: {{parametros}}, reason: [razón]
(Si no necesita llamar tools adicionales, escribe: Ninguna)

PARAM_VALIDATION:
- tool: [nombre_tool_ya_ejecutada], param: [nombre_parametro], issue: [problema con el parámetro], suggested: [valor sugerido]
(Si los parámetros de las tools ejecutadas están bien, escribe: Ninguna)

CONTINUE_IMPROVING: [YES o NO]
(YES si la respuesta aún puede mejorar significativamente con otra iteración.
 NO si la respuesta ya es suficientemente buena y completa.
 En Loop 1, tu decisión no afecta - siempre se ejecuta mejora.
 En Loop 2+, NO detendrá el proceso de mejora.)

FEEDBACK:
[SIEMPRE explica cómo podría mejorar el agente principal.
Sé específico y constructivo. Este feedback se usará para la siguiente iteración.
Ejemplo: "Falta incluir el presupuesto de la licitación 123456-2024"]
```

**IMPORTANTE:**
- El SCORE es SOLO para análisis, NO determina si continuar o no
- CONTINUE_IMPROVING es TU decisión como revisor experto:
  * YES: La respuesta puede mejorar significativamente
  * NO: La respuesta ya es suficientemente buena
- El FEEDBACK es OBLIGATORIO siempre, incluso si dices NO a continuar
- En TOOL_SUGGESTIONS, recomienda tools específicas que ayudarían
- En PARAM_VALIDATION, verifica si los parámetros usados fueron óptimos
- NO reescribas la respuesta, solo da feedback para que el agente la mejore

**HERRAMIENTAS DISPONIBLES:**
- find_best_tender(query): Encuentra LA mejor licitación (singular)
- find_top_tenders(query, limit): Encuentra X mejores licitaciones (plural)
- get_tender_details(tender_id): Obtiene información detallada de una licitación específica
- find_by_budget(min_budget, max_budget): Busca por rango de presupuesto
- find_by_deadline(days_ahead): Busca por fecha límite
- get_company_info(): Obtiene información de la empresa del usuario
- compare_tenders(tender_ids): Compara múltiples licitaciones
"""

        return prompt

    def _format_conversation_history(self, conversation_history: List[Dict[str, str]]) -> str:
        """Formatea el historial de conversación para el prompt."""
        if not conversation_history:
            return "(Sin historial previo)"

        # Limitar a últimos 5 mensajes para no saturar
        recent_history = conversation_history[-5:]

        formatted = []
        for msg in recent_history:
            role = "Usuario" if msg['role'] == 'user' else "Asistente"
            content_preview = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
            formatted.append(f"{role}: {content_preview}")

        return "\n".join(formatted)

    def _parse_review_response(self, review_text: str) -> Dict[str, Any]:
        """
        Parsea la respuesta del LLM revisor.

        Args:
            review_text: Texto de respuesta del LLM revisor

        Returns:
            Dict con feedback, score, issues, suggestions, continue_improving
        """
        try:
            # Valores por defecto
            score = 100
            issues = []
            suggestions = []
            tool_suggestions = []
            param_validation = []
            feedback = ''
            continue_improving = True  # Default: continuar mejorando

            lines = review_text.strip().split('\n')

            current_section = None

            for line in lines:
                line = line.strip()

                # Detectar secciones
                if line.startswith('SCORE:'):
                    try:
                        # Extraer solo el número
                        score_text = line.replace('SCORE:', '').strip()
                        # Tomar primer token numérico
                        score = float(score_text.split()[0])
                    except (ValueError, IndexError):
                        score = 75  # Default si no se puede parsear
                    current_section = None

                elif line.startswith('ISSUES:'):
                    current_section = 'issues'

                elif line.startswith('SUGGESTIONS:'):
                    current_section = 'suggestions'

                elif line.startswith('TOOL_SUGGESTIONS:'):
                    current_section = 'tool_suggestions'

                elif line.startswith('PARAM_VALIDATION:'):
                    current_section = 'param_validation'

                elif line.startswith('CONTINUE_IMPROVING:'):
                    decision_text = line.replace('CONTINUE_IMPROVING:', '').strip().upper()
                    if 'NO' in decision_text:
                        continue_improving = False
                    else:
                        continue_improving = True
                    current_section = None

                elif line.startswith('FEEDBACK:'):
                    current_section = 'feedback'

                # Agregar contenido a secciones
                elif line.startswith('-') and current_section in ['issues', 'suggestions', 'tool_suggestions', 'param_validation']:
                    content = line[1:].strip()
                    if content.lower() not in ['ninguno', 'ninguna', 'none']:
                        if current_section == 'issues':
                            issues.append(content)
                        elif current_section == 'suggestions':
                            suggestions.append(content)
                        elif current_section == 'tool_suggestions':
                            # Parse: tool: nombre, params: {...}, reason: ...
                            tool_suggestions.append(self._parse_tool_suggestion(content))
                        elif current_section == 'param_validation':
                            # Parse: tool: nombre, param: ..., issue: ..., suggested: ...
                            param_validation.append(self._parse_param_validation(content))

                elif current_section == 'feedback' and line:
                    if not line.startswith('```'):  # Ignorar marcadores de código
                        feedback += line + ' '

            # Limpiar feedback
            feedback = feedback.strip()
            # No limpiar feedback vacío - SIEMPRE debe haber feedback

            return {
                'feedback': feedback,
                'score': score,
                'issues': issues,
                'suggestions': suggestions,
                'tool_suggestions': tool_suggestions,
                'param_validation': param_validation,
                'continue_improving': continue_improving
            }

        except Exception as e:
            logger.error(f"[REVIEWER] Error parseando respuesta del revisor: {e}")
            # Fallback seguro
            return {
                'feedback': 'Error al parsear respuesta del revisor',
                'score': 100,
                'issues': [],
                'suggestions': [],
                'tool_suggestions': [],
                'param_validation': [],
                'continue_improving': False,  # No continuar si hay error
                'parse_error': str(e)
            }

    def _parse_tool_suggestion(self, content: str) -> Dict[str, Any]:
        """
        Parsea una sugerencia de tool.
        Formato esperado: tool: nombre, params: {...}, reason: ...
        """
        try:
            parts = {}
            # Dividir por comas pero respetando {...}
            current_key = None
            current_value = ""
            in_braces = 0

            for char in content:
                if char == '{':
                    in_braces += 1
                    current_value += char
                elif char == '}':
                    in_braces -= 1
                    current_value += char
                elif char == ',' and in_braces == 0:
                    # Fin de un par key:value
                    if ':' in current_value:
                        key, val = current_value.split(':', 1)
                        parts[key.strip()] = val.strip()
                    current_value = ""
                else:
                    current_value += char

            # Último par
            if current_value and ':' in current_value:
                key, val = current_value.split(':', 1)
                parts[key.strip()] = val.strip()

            return {
                'tool': parts.get('tool', 'unknown'),
                'params': parts.get('params', '{}'),
                'reason': parts.get('reason', '')
            }
        except Exception as e:
            logger.warning(f"[REVIEWER] Error parseando tool suggestion: {e}")
            return {'tool': content, 'params': '{}', 'reason': ''}

    def _parse_param_validation(self, content: str) -> Dict[str, Any]:
        """
        Parsea una validación de parámetro.
        Formato esperado: tool: nombre, param: ..., issue: ..., suggested: ...
        """
        try:
            parts = {}
            current_value = ""

            for char in content:
                if char == ',' and ':' in current_value:
                    key, val = current_value.split(':', 1)
                    parts[key.strip()] = val.strip()
                    current_value = ""
                else:
                    current_value += char

            # Último par
            if current_value and ':' in current_value:
                key, val = current_value.split(':', 1)
                parts[key.strip()] = val.strip()

            return {
                'tool': parts.get('tool', 'unknown'),
                'param': parts.get('param', ''),
                'issue': parts.get('issue', ''),
                'suggested': parts.get('suggested', '')
            }
        except Exception as e:
            logger.warning(f"[REVIEWER] Error parseando param validation: {e}")
            return {'tool': content, 'param': '', 'issue': '', 'suggested': ''}
