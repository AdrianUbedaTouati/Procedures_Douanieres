"""
Funciones auxiliares para búsquedas semánticas.

Estas funciones NO son tools, son utilidades internas que las tools pueden reutilizar.
"""

from typing import Dict, Any, List
from collections import Counter
import logging

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
