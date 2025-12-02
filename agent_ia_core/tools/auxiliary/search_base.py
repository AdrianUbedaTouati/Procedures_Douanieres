"""
Funciones auxiliares para búsquedas semánticas.

Estas funciones NO son tools, son utilidades internas que las tools pueden reutilizar.
"""

from typing import Dict, Any, List, Optional
from collections import Counter
import logging
import json

logger = logging.getLogger(__name__)


def semantic_search_single(query: str, vectorstore, k: int = 7) -> Dict[str, Any]:
    """
    Búsqueda semántica que retorna UN solo documento (el que tiene más chunks en top-K).

    Algoritmo:
    1. Buscar top-K chunks con similarity_search
    2. Contar frecuencia de aparición de cada documento
    3. Seleccionar el documento con más chunks en top-K

    Args:
        query: Consulta de búsqueda semántica
        vectorstore: ChromaDB vectorstore o HybridRetriever
        k: Número de chunks a buscar (default: 7)

    Returns:
        Dict con formato:
        {
            'success': bool,
            'document': {
                'id': str,
                'content': str,
                'metadata': dict,
                'chunk_count': int,
                'best_score': float
            } | None,
            'error': str (si success=False)
        }
    """
    try:
        logger.info(f"[SEARCH_SINGLE] Buscando top-{k} chunks para: '{query[:50]}...'")

        # Si es HybridRetriever, extraer el vectorstore interno
        if hasattr(vectorstore, 'vectorstore'):
            actual_vectorstore = vectorstore.vectorstore
        else:
            actual_vectorstore = vectorstore

        # Buscar top K chunks
        results = actual_vectorstore.similarity_search_with_score(query, k=k)

        if not results:
            logger.warning("[SEARCH_SINGLE] No se encontraron resultados")
            return {
                'success': False,
                'error': 'No se encontraron documentos relevantes',
                'document': None
            }

        # Contar frecuencia de documentos
        doc_chunks = {}
        for doc, score in results:
            doc_id = doc.metadata.get('ojs_notice_id', 'unknown')
            if doc_id not in doc_chunks:
                doc_chunks[doc_id] = {
                    'count': 0,
                    'doc': doc,
                    'best_score': score,
                    'chunks': []
                }
            doc_chunks[doc_id]['count'] += 1
            doc_chunks[doc_id]['best_score'] = min(doc_chunks[doc_id]['best_score'], score)
            doc_chunks[doc_id]['chunks'].append({'content': doc.page_content, 'score': score})

        # Seleccionar documento con más chunks
        best_doc_id = max(doc_chunks.keys(), key=lambda x: doc_chunks[x]['count'])
        best_doc_entry = doc_chunks[best_doc_id]

        logger.info(f"[SEARCH_SINGLE] ✓ Documento seleccionado: {best_doc_id} "
                   f"({best_doc_entry['count']} chunks en top-{k})")

        return {
            'success': True,
            'document': {
                'id': best_doc_id,
                'content': best_doc_entry['doc'].page_content,
                'metadata': best_doc_entry['doc'].metadata,
                'chunk_count': best_doc_entry['count'],
                'best_score': best_doc_entry['best_score'],
                'chunks': best_doc_entry['chunks']
            }
        }

    except Exception as e:
        logger.error(f"[SEARCH_SINGLE] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'document': None
        }


def semantic_search_multiple(
    query: str,
    vectorstore,
    limit: int = 5,
    k_per_doc: int = 7
) -> Dict[str, Any]:
    """
    Búsqueda semántica que retorna múltiples documentos únicos.

    Algoritmo:
    1. Buscar limit * k_per_doc chunks totales
    2. Agrupar por documento y contar frecuencia
    3. Ordenar por chunk_count (descendente)
    4. Retornar top N documentos únicos

    Args:
        query: Consulta de búsqueda semántica
        vectorstore: ChromaDB vectorstore o HybridRetriever
        limit: Número máximo de documentos a retornar (default: 5)
        k_per_doc: Chunks por documento a considerar (default: 7)

    Returns:
        Dict con formato:
        {
            'success': bool,
            'documents': [
                {
                    'id': str,
                    'content': str,
                    'metadata': dict,
                    'chunk_count': int,
                    'best_score': float
                },
                ...
            ],
            'error': str (si success=False)
        }
    """
    try:
        total_k = limit * k_per_doc
        logger.info(f"[SEARCH_MULTIPLE] Buscando top-{total_k} chunks para: '{query[:50]}...'")

        # Si es HybridRetriever, extraer el vectorstore interno
        if hasattr(vectorstore, 'vectorstore'):
            actual_vectorstore = vectorstore.vectorstore
        else:
            actual_vectorstore = vectorstore

        results = actual_vectorstore.similarity_search_with_score(query, k=total_k)

        if not results:
            logger.warning("[SEARCH_MULTIPLE] No se encontraron resultados")
            return {
                'success': False,
                'error': 'No se encontraron documentos relevantes',
                'documents': []
            }

        # Agrupar por documento
        doc_chunks = {}
        for doc, score in results:
            doc_id = doc.metadata.get('ojs_notice_id', 'unknown')
            if doc_id not in doc_chunks:
                doc_chunks[doc_id] = {
                    'count': 0,
                    'doc': doc,
                    'best_score': score
                }
            doc_chunks[doc_id]['count'] += 1
            doc_chunks[doc_id]['best_score'] = min(doc_chunks[doc_id]['best_score'], score)

        # Ordenar por chunk count (descendente)
        sorted_docs = sorted(
            doc_chunks.items(),
            key=lambda x: (x[1]['count'], -x[1]['best_score']),  # Más chunks = mejor
            reverse=True
        )

        # Tomar top N
        top_docs = sorted_docs[:limit]

        documents = []
        for doc_id, doc_entry in top_docs:
            documents.append({
                'id': doc_id,
                'content': doc_entry['doc'].page_content,
                'metadata': doc_entry['doc'].metadata,
                'chunk_count': doc_entry['count'],
                'best_score': doc_entry['best_score']
            })

        logger.info(f"[SEARCH_MULTIPLE] ✓ {len(documents)} documentos seleccionados")

        return {
            'success': True,
            'documents': documents
        }

    except Exception as e:
        logger.error(f"[SEARCH_MULTIPLE] Error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'documents': []
        }


def optimize_and_search_iterative_with_verification(
    original_query: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    tool_calls_history: Optional[List[Dict[str, Any]]] = None,
    company_info: Optional[Dict[str, Any]] = None,
    vectorstore=None,
    llm=None,
    user=None,
    mode: str = "single",
    limit: int = 5
) -> Dict[str, Any]:
    """
    Realiza 5 búsquedas SECUENCIALES con verificación de contenido completo.

    Proceso por iteración:
    1. LLM genera query optimizada (considerando resultados previos)
    2. semantic_search_single → obtiene doc_id + chunk_count
    3. get_tender_details(doc_id) → obtiene resumen completo del documento
    4. LLM analiza contenido completo → ¿corresponde? puntuación 0-10
    5. Feedback al LLM para siguiente búsqueda

    Al final, selecciona el/los mejor(es) documento(s) basándose en:
    - Puntuación del LLM (verificación de contenido)
    - Chunk_count (relevancia semántica)
    - Apariciones múltiples (confiabilidad)

    Args:
        original_query: Query original del usuario
        conversation_history: Historial de mensajes del chat
        tool_calls_history: Historial de tool calls [{tool_name, parameters, result}, ...]
        company_info: Información de la empresa del usuario
        vectorstore: ChromaDB vectorstore o HybridRetriever
        llm: Instancia del LLM para optimización
        user: Usuario de Django (para get_tender_details)
        mode: "single" (1 documento) o "multiple" (X documentos)
        limit: Número de documentos a retornar si mode="multiple"

    Returns:
        Dict con formato:
        {
            'success': bool,
            'best_documents': [...],  # 1 doc si mode="single", X si "multiple"
            'search_iterations': [
                {
                    'iteration': 1,
                    'query': "...",
                    'doc_id': "doc_A",
                    'chunk_count': 3,
                    'tender_summary': {...},
                    'corresponds': true,
                    'score': 9,
                    'reasoning': "..."
                },
                ...
            ],
            'analysis': {
                'total_searches': 5,
                'unique_documents': 3,
                'best_doc_appearances': 3,
                'chunk_progression': [3, 5, 6],
                'is_reliable': bool,
                'clarification_request': str | None,
                'confidence_score': float
            }
        }
    """
    try:
        if not llm or not vectorstore:
            logger.error("[ITERATIVE_SEARCH] LLM o vectorstore no disponibles")
            return _fallback_search(original_query, vectorstore, mode, limit)

        logger.info(f"[ITERATIVE_SEARCH] Iniciando 5 búsquedas secuenciales para: '{original_query[:50]}...'")
        logger.info(f"[ITERATIVE_SEARCH] Modo: {mode}, Limit: {limit if mode == 'multiple' else 1}")

        # ============================================================
        # FASE 1: PREPARAR CONTEXTO COMPLETO
        # ============================================================

        context = _build_full_context(
            conversation_history=conversation_history,
            tool_calls_history=tool_calls_history,
            company_info=company_info
        )

        # ============================================================
        # FASE 2: REALIZAR 5 BÚSQUEDAS SECUENCIALES
        # ============================================================

        search_iterations = []
        conversation_with_llm = [
            {
                "role": "system",
                "content": f"""Eres un experto en optimización de búsquedas semánticas en bases de datos de licitaciones públicas (ChromaDB).

CONTEXTO DISPONIBLE:
{context}

TU TAREA:
Vas a realizar 5 búsquedas SECUENCIALES para encontrar {"LA mejor licitación" if mode == "single" else f"LAS {limit} mejores licitaciones"}.

PROCESO POR BÚSQUEDA:
1. Generas una query optimizada para ChromaDB
2. Recibes: documento encontrado + chunk_count (1=poco fiable, 2=fiable, 3+=muy fiable)
3. Recibes: CONTENIDO COMPLETO de la licitación (título, descripción, presupuesto, ubicación, etc.)
4. Analizas si REALMENTE corresponde a lo que busca el usuario
5. Puntúas de 0-10 basándote en correspondencia real
6. Usas feedback para mejorar siguiente búsqueda

QUERY ORIGINAL DEL USUARIO:
"{original_query}"

Comenzamos con la BÚSQUEDA 1/5.
Genera una query optimizada para ChromaDB (búsqueda semántica vectorial).
Responde SOLO con la query, sin explicaciones adicionales."""
            }
        ]

        # Importar get_tender_details para verificación
        from ..get_tender_details import get_tender_details

        # Realizar 5 búsquedas secuenciales
        for iteration in range(1, 6):
            logger.info(f"[ITERATIVE_SEARCH] === Búsqueda {iteration}/5 ===")

            # 1. Pedir al LLM que genere la query optimizada
            llm_response = llm.invoke(conversation_with_llm)
            optimized_query = llm_response.content.strip()

            # Agregar query del LLM al historial
            conversation_with_llm.append({
                "role": "assistant",
                "content": optimized_query
            })

            logger.info(f"[ITERATIVE_SEARCH] Query {iteration}: '{optimized_query[:80]}...'")

            # 2. Ejecutar búsqueda semántica
            search_result = semantic_search_single(
                query=optimized_query,
                vectorstore=vectorstore,
                k=7
            )

            # Evaluar resultado
            if search_result['success']:
                doc = search_result['document']
                doc_id = doc['id']
                chunk_count = doc['chunk_count']

                logger.info(f"[ITERATIVE_SEARCH] Documento encontrado: {doc_id} ({chunk_count} chunks)")

                # 3. Obtener detalles completos del documento
                tender_details_result = get_tender_details(document_id=doc_id, user=user)

                if tender_details_result.get('success'):
                    tender_data = tender_details_result.get('data', {})

                    # Formatear resumen para el LLM
                    tender_summary = f"""ID: {tender_data.get('id', 'N/A')}
Título: {tender_data.get('title', 'N/A')}
Descripción: {tender_data.get('description', 'N/A')[:500]}...
Comprador: {tender_data.get('buyer_name', 'N/A')}
CPV: {tender_data.get('cpv_codes', 'N/A')}
Ubicación (NUTS): {tender_data.get('nuts_regions', 'N/A')}
Presupuesto: {tender_data.get('budget_eur', 'N/A')} EUR
Fecha límite: {tender_data.get('tender_deadline_date', 'N/A')}
Tipo contrato: {tender_data.get('contract_type', 'N/A')}"""

                    logger.info(f"[ITERATIVE_SEARCH] Detalles obtenidos para {doc_id}")

                    # 4. LLM analiza si corresponde
                    analysis_prompt = f"""RESULTADO BÚSQUEDA {iteration}:

Usuario busca: "{original_query}"

Documento encontrado:
- Chunk_count: {chunk_count} ({"POCO FIABLE" if chunk_count == 1 else "FIABLE" if chunk_count == 2 else "MUY FIABLE"})

CONTENIDO COMPLETO:
{tender_summary}

¿Este documento REALMENTE corresponde a lo que busca el usuario?

Responde en formato JSON:
{{
    "corresponds": true/false,
    "score": 0-10,
    "reasoning": "explicación breve de por qué corresponde o no",
    "missing_info": "qué información falta o qué no corresponde (null si todo OK)"
}}"""

                    analysis_response = llm.invoke([{"role": "user", "content": analysis_prompt}])
                    analysis = _parse_llm_json(analysis_response.content)

                    # Determinar fiabilidad por chunk_count
                    if chunk_count == 1:
                        reliability = "POCO FIABLE"
                    elif chunk_count == 2:
                        reliability = "FIABLE"
                    else:
                        reliability = "MUY FIABLE"

                    iteration_result = {
                        'iteration': iteration,
                        'query': optimized_query,
                        'doc_id': doc_id,
                        'chunk_count': chunk_count,
                        'score': doc['best_score'],
                        'reliability': reliability,
                        'tender_summary': tender_data,
                        'corresponds': analysis.get('corresponds', False),
                        'llm_score': analysis.get('score', 0),
                        'reasoning': analysis.get('reasoning', ''),
                        'missing_info': analysis.get('missing_info'),
                        'document': doc
                    }

                    logger.info(f"[ITERATIVE_SEARCH] ✓ Búsqueda {iteration}: {doc_id} | "
                               f"Chunks: {chunk_count} ({reliability}) | "
                               f"Corresponde: {analysis.get('corresponds')} | "
                               f"Puntuación LLM: {analysis.get('score')}/10")

                else:
                    # Error obteniendo detalles
                    logger.warning(f"[ITERATIVE_SEARCH] Error obteniendo detalles de {doc_id}")
                    iteration_result = {
                        'iteration': iteration,
                        'query': optimized_query,
                        'doc_id': doc_id,
                        'chunk_count': chunk_count,
                        'reliability': 'FIABLE' if chunk_count >= 2 else 'POCO FIABLE',
                        'tender_summary': {},
                        'corresponds': False,
                        'llm_score': 0,
                        'reasoning': 'No se pudieron obtener detalles del documento',
                        'document': doc
                    }
            else:
                # Sin resultados
                logger.warning(f"[ITERATIVE_SEARCH] ✗ Búsqueda {iteration}: sin resultados")
                iteration_result = {
                    'iteration': iteration,
                    'query': optimized_query,
                    'doc_id': None,
                    'chunk_count': 0,
                    'reliability': 'SIN RESULTADOS',
                    'tender_summary': {},
                    'corresponds': False,
                    'llm_score': 0,
                    'reasoning': 'No se encontraron documentos',
                    'document': None
                }

            search_iterations.append(iteration_result)

            # 5. Feedback al LLM para próxima iteración (si no es la última)
            if iteration < 5:
                # Calcular mejor documento hasta ahora
                docs_so_far = [it for it in search_iterations if it['doc_id']]
                if docs_so_far:
                    best_so_far = max(docs_so_far, key=lambda x: x['llm_score'])
                    best_summary = f"{best_so_far['doc_id']} ({best_so_far['llm_score']}/10)"
                else:
                    best_summary = "Ninguno encontrado aún"

                feedback = f"""RESULTADO BÚSQUEDA {iteration}:
- Documento: {iteration_result['doc_id'] or 'NINGUNO'}
- Chunks: {iteration_result['chunk_count']} ({iteration_result['reliability']})
- Corresponde: {iteration_result['corresponds']}
- Puntuación: {iteration_result['llm_score']}/10
- Análisis: {iteration_result['reasoning']}

{"✓ Buen resultado. " if iteration_result['llm_score'] >= 7 else "✗ Resultado débil. " if iteration_result['doc_id'] else "Sin resultados. "}Mejor documento hasta ahora: {best_summary}

Genera query para BÚSQUEDA {iteration + 1}/5 con un enfoque diferente.
Responde SOLO con la query."""

                conversation_with_llm.append({
                    "role": "user",
                    "content": feedback
                })

        # ============================================================
        # FASE 3: ANÁLISIS FINAL Y SELECCIÓN
        # ============================================================

        logger.info(f"[ITERATIVE_SEARCH] Analizando resultados de 5 búsquedas...")

        # Filtrar solo documentos encontrados
        found_docs = [it for it in search_iterations if it['doc_id']]

        if not found_docs:
            logger.warning("[ITERATIVE_SEARCH] No se encontraron documentos en ninguna búsqueda")
            return {
                'success': True,
                'best_documents': [],
                'search_iterations': search_iterations,
                'analysis': {
                    'total_searches': 5,
                    'unique_documents': 0,
                    'is_reliable': False,
                    'clarification_request': 'No se encontraron licitaciones relevantes. Intenta con términos más específicos o diferentes.'
                }
            }

        # Preparar resumen para análisis final
        summary = f"""Has completado 5 búsquedas secuenciales. Aquí está el resumen:

"""
        for it in search_iterations:
            if it['doc_id']:
                summary += f"""- Búsqueda {it['iteration']}: {it['doc_id']}
  Chunks: {it['chunk_count']} ({it['reliability']})
  Corresponde: {it['corresponds']}
  Puntuación: {it['llm_score']}/10
  Razón: {it['reasoning']}

"""
            else:
                summary += f"- Búsqueda {it['iteration']}: SIN RESULTADOS\n\n"

        summary += f"""
Ahora debes seleccionar {"EL MEJOR documento (1 solo)" if mode == "single" else f"LOS MEJORES {limit} documentos únicos"}.

CRITERIOS DE SELECCIÓN:
1. Mayor puntuación LLM (verificación de contenido real)
2. Mayor chunk_count (relevancia semántica)
3. Si un documento apareció en múltiples búsquedas = más confiable
4. Documentos que "corresponds: true" tienen prioridad

IMPORTANTE:
- Evalúa si la información original del usuario era suficiente
- Si era vaga, indica qué información adicional mejoraría la búsqueda

Responde en formato JSON:
{{
    "selected_document_ids": {'"doc_id"' if mode == "single" else '["doc_id1", "doc_id2", ...]'},
    "reasoning": "por qué seleccionaste estos documentos",
    "is_reliable": true/false,
    "clarification_request": "qué info adicional necesitas (null si is_reliable=true)",
    "confidence_score": 0.0-1.0
}}"""

        conversation_with_llm.append({
            "role": "user",
            "content": summary
        })

        # Obtener análisis final del LLM
        final_response = llm.invoke(conversation_with_llm)
        final_analysis = _parse_llm_json(final_response.content)

        # Recuperar documentos seleccionados
        selected_ids = final_analysis.get('selected_document_ids', [])
        if isinstance(selected_ids, str):  # Si es un solo ID como string
            selected_ids = [selected_ids]

        # Agrupar iteraciones por doc_id para análisis
        doc_occurrences = {}
        for it in found_docs:
            doc_id = it['doc_id']
            if doc_id not in doc_occurrences:
                doc_occurrences[doc_id] = []
            doc_occurrences[doc_id].append(it)

        # Seleccionar documentos
        best_documents = []
        chunk_progression = {}

        for doc_id in selected_ids:
            if doc_id in doc_occurrences:
                # Tomar la iteración con mejor chunk_count
                best_iteration = max(doc_occurrences[doc_id], key=lambda x: x['chunk_count'])
                best_documents.append(best_iteration['document'])
                chunk_progression[doc_id] = [it['chunk_count'] for it in doc_occurrences[doc_id]]

        # Limitar a N documentos
        best_documents = best_documents[:limit] if mode == "multiple" else best_documents[:1]

        # Calcular métricas
        unique_docs = len(doc_occurrences)
        best_doc_id = selected_ids[0] if selected_ids else None
        best_doc_appearances = len(doc_occurrences.get(best_doc_id, [])) if best_doc_id else 0

        logger.info(f"[ITERATIVE_SEARCH] ✓ Seleccionados {len(best_documents)} documento(s)")
        logger.info(f"[ITERATIVE_SEARCH] Documentos únicos encontrados: {unique_docs}")
        logger.info(f"[ITERATIVE_SEARCH] Confianza: {final_analysis.get('confidence_score', 0.5)}")

        return {
            'success': True,
            'best_documents': best_documents,
            'search_iterations': search_iterations,
            'analysis': {
                'total_searches': 5,
                'unique_documents': unique_docs,
                'selected_count': len(best_documents),
                'best_doc_appearances': best_doc_appearances,
                'chunk_progression': chunk_progression,
                'reasoning': final_analysis.get('reasoning'),
                'is_reliable': final_analysis.get('is_reliable', True),
                'clarification_request': final_analysis.get('clarification_request'),
                'confidence_score': final_analysis.get('confidence_score', 0.5)
            }
        }

    except Exception as e:
        logger.error(f"[ITERATIVE_SEARCH] Error: {e}", exc_info=True)
        return _fallback_search(original_query, vectorstore, mode, limit)


def _build_full_context(conversation_history, tool_calls_history, company_info):
    """Construye contexto completo para el LLM intermediario."""
    context = ""

    # Información de empresa
    if company_info:
        context += f"""
INFORMACIÓN DE LA EMPRESA:
- Nombre: {company_info.get('name', 'N/A')}
- Sector: {company_info.get('sector', 'N/A')}
- Descripción: {company_info.get('description', 'N/A')}
- Especialización: {company_info.get('specialization', 'N/A')}
"""

    # Historial de conversación (últimos 10 mensajes)
    if conversation_history and len(conversation_history) > 0:
        recent = conversation_history[-10:]
        context += "\nHISTORIAL DE CONVERSACIÓN (últimos mensajes):\n"
        for msg in recent:
            role = msg.get('role', 'user')
            content = msg.get('content', '')[:200]
            context += f"- [{role}]: {content}...\n"

    # Historial de tool calls (últimas 5)
    if tool_calls_history and len(tool_calls_history) > 0:
        recent_tools = tool_calls_history[-5:]
        context += "\nFUNCIONES EJECUTADAS RECIENTEMENTE:\n"
        for tc in recent_tools:
            tool_name = tc.get('tool_name', 'unknown')
            params = tc.get('parameters', {})
            result = tc.get('result', {})

            # Resumen del resultado
            result_summary = ""
            if isinstance(result, dict):
                if result.get('success'):
                    result_summary = f"✓ {result.get('message', 'OK')[:100]}"
                else:
                    result_summary = f"✗ {result.get('error', 'Error')[:100]}"

            context += f"- {tool_name}({params}) → {result_summary}\n"

    return context


def _parse_llm_json(response_text: str) -> dict:
    """Parsea respuesta JSON del LLM (maneja ```json ... ```)."""
    try:
        json_text = response_text.strip()
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0].strip()
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0].strip()

        return json.loads(json_text)
    except Exception as e:
        logger.warning(f"[PARSE_JSON] Error parseando JSON: {e}")
        logger.warning(f"[PARSE_JSON] Texto raw: {response_text[:200]}...")
        return {}


def _fallback_search(original_query, vectorstore, mode, limit):
    """Búsqueda de respaldo si falla el sistema iterativo."""
    logger.warning("[ITERATIVE_SEARCH] Usando búsqueda de respaldo (sin optimización)")

    if mode == "single":
        result = semantic_search_single(query=original_query, vectorstore=vectorstore, k=7)
        return {
            'success': result['success'],
            'best_documents': [result['document']] if result['success'] else [],
            'search_iterations': [],
            'analysis': {'fallback': True, 'is_reliable': True}
        }
    else:
        result = semantic_search_multiple(query=original_query, vectorstore=vectorstore, limit=limit, k_per_doc=7)
        return {
            'success': result['success'],
            'best_documents': result['documents'],
            'search_iterations': [],
            'analysis': {'fallback': True, 'is_reliable': True}
        }
