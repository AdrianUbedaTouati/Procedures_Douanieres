# -*- coding: utf-8 -*-
"""
LLM Revisor de Respuestas - Sistema de Auto-mejora
Revisa formato y contenido de las respuestas del agente principal.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ResponseReviewer:
    """
    Revisor inteligente que analiza respuestas del agente principal.

    Revisa:
    - Formato: Markdown correcto, estructura clara
    - Contenido: Completitud, precisión, relevancia
    - Coherencia: Responde la pregunta, usa documentos correctamente
    """

    def __init__(self, llm):
        """
        Inicializa el revisor con un LLM.

        Args:
            llm: Instancia del LLM (ChatOllama, ChatOpenAI, ChatGemini, etc.)
        """
        self.llm = llm

    def review_response(
        self,
        user_question: str,
        conversation_history: List[Dict[str, str]],
        initial_response: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Revisa una respuesta del agente principal.

        Args:
            user_question: Pregunta original del usuario
            conversation_history: Historial de la conversación
            initial_response: Respuesta inicial generada por el agente
            metadata: Metadatos (documentos usados, tools, etc.)

        Returns:
            Dict con formato:
            {
                'status': 'APPROVED' | 'NEEDS_IMPROVEMENT',
                'feedback': str,  # Solo si NEEDS_IMPROVEMENT
                'score': float (0-100),
                'issues': List[str],  # Problemas detectados
                'suggestions': List[str]  # Sugerencias de mejora
            }
        """
        logger.info("[REVIEWER] Iniciando revisión de respuesta...")

        try:
            # Construir prompt de revisión
            review_prompt = self._build_review_prompt(
                user_question=user_question,
                conversation_history=conversation_history,
                initial_response=initial_response,
                metadata=metadata
            )

            # Llamar al LLM revisor
            logger.info("[REVIEWER] Llamando al LLM revisor...")
            review_result = self.llm.invoke(review_prompt)

            # Parsear respuesta del revisor
            parsed_review = self._parse_review_response(review_result.content)

            logger.info(
                f"[REVIEWER] Revisión completada: {parsed_review['status']} "
                f"(score: {parsed_review['score']}/100)"
            )

            return parsed_review

        except Exception as e:
            logger.error(f"[REVIEWER] Error en revisión: {e}", exc_info=True)
            # Fallback: aprobar respuesta si hay error
            return {
                'status': 'APPROVED',
                'feedback': '',
                'score': 100,
                'issues': [],
                'suggestions': [],
                'error': str(e)
            }

    def _build_review_prompt(
        self,
        user_question: str,
        conversation_history: List[Dict[str, str]],
        initial_response: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Construye el prompt de revisión para el LLM revisor."""

        # Formatear historial
        history_text = self._format_conversation_history(conversation_history)

        # Información de documentos
        docs_info = ""
        if metadata.get('documents_used'):
            docs_info = f"\n\n**Documentos consultados:** {len(metadata['documents_used'])} documentos"
            docs_ids = [doc.get('id', 'unknown') for doc in metadata['documents_used'][:5]]
            docs_info += f"\nIDs: {', '.join(docs_ids)}"

        # Información de tools
        tools_info = ""
        if metadata.get('tools_used'):
            tools_info = f"\n\n**Herramientas usadas:** {', '.join(metadata['tools_used'])}"

        prompt = f"""Eres un **revisor experto de respuestas de chatbot sobre licitaciones públicas**.

Tu tarea es revisar la respuesta generada por el agente principal y determinar si está bien o necesita mejoras.

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
STATUS: [APPROVED o NEEDS_IMPROVEMENT]
SCORE: [0-100]

ISSUES:
- [Problema 1 si existe]
- [Problema 2 si existe]
(Si no hay problemas, escribe: Ninguno)

SUGGESTIONS:
- [Sugerencia 1 si existe]
- [Sugerencia 2 si existe]
(Si no hay sugerencias, escribe: Ninguna)

FEEDBACK:
[Si STATUS = NEEDS_IMPROVEMENT, explica QUÉ debe mejorar el agente principal.
Si STATUS = APPROVED, deja esta sección vacía o escribe "Respuesta correcta"]
```

**IMPORTANTE:**
- Si score >= 75 → STATUS debe ser APPROVED
- Si score < 75 → STATUS debe ser NEEDS_IMPROVEMENT
- En FEEDBACK, sé específico: "Falta incluir el presupuesto de la licitación 00123456"
- NO reescribas la respuesta, solo da feedback al agente para que él la mejore

**NOTA:** El agente SIEMPRE ejecutará una segunda iteración de mejora independientemente del score.
Así que incluso si la respuesta está bien (APPROVED), proporciona sugerencias constructivas para hacerla aún mejor.
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
            Dict con status, feedback, score, issues, suggestions
        """
        try:
            # Valores por defecto
            status = 'APPROVED'
            score = 100
            issues = []
            suggestions = []
            feedback = ''

            lines = review_text.strip().split('\n')

            current_section = None

            for line in lines:
                line = line.strip()

                # Detectar secciones
                if line.startswith('STATUS:'):
                    status_text = line.replace('STATUS:', '').strip()
                    if 'NEEDS_IMPROVEMENT' in status_text.upper():
                        status = 'NEEDS_IMPROVEMENT'
                    else:
                        status = 'APPROVED'
                    current_section = None

                elif line.startswith('SCORE:'):
                    try:
                        score = float(line.replace('SCORE:', '').strip())
                    except ValueError:
                        score = 75  # Default si no se puede parsear
                    current_section = None

                elif line.startswith('ISSUES:'):
                    current_section = 'issues'

                elif line.startswith('SUGGESTIONS:'):
                    current_section = 'suggestions'

                elif line.startswith('FEEDBACK:'):
                    current_section = 'feedback'

                # Agregar contenido a secciones
                elif line.startswith('-') and current_section in ['issues', 'suggestions']:
                    content = line[1:].strip()
                    if content.lower() not in ['ninguno', 'ninguna', 'none']:
                        if current_section == 'issues':
                            issues.append(content)
                        elif current_section == 'suggestions':
                            suggestions.append(content)

                elif current_section == 'feedback' and line:
                    if not line.startswith('```'):  # Ignorar marcadores de código
                        feedback += line + ' '

            # Limpiar feedback
            feedback = feedback.strip()
            if feedback.lower() in ['respuesta correcta', 'ninguno', 'ninguna']:
                feedback = ''

            # Ajustar status según score si hay inconsistencia
            if score >= 75 and status == 'NEEDS_IMPROVEMENT':
                logger.warning(f"[REVIEWER] Inconsistencia: score={score} pero status=NEEDS_IMPROVEMENT. Ajustando a APPROVED")
                status = 'APPROVED'
            elif score < 75 and status == 'APPROVED':
                logger.warning(f"[REVIEWER] Inconsistencia: score={score} pero status=APPROVED. Ajustando a NEEDS_IMPROVEMENT")
                status = 'NEEDS_IMPROVEMENT'

            return {
                'status': status,
                'feedback': feedback,
                'score': score,
                'issues': issues,
                'suggestions': suggestions
            }

        except Exception as e:
            logger.error(f"[REVIEWER] Error parseando respuesta del revisor: {e}")
            # Fallback seguro
            return {
                'status': 'APPROVED',
                'feedback': '',
                'score': 100,
                'issues': [],
                'suggestions': [],
                'parse_error': str(e)
            }
