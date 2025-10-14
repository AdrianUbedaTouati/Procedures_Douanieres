# -*- coding: utf-8 -*-
"""
Retriever híbrido para búsqueda de chunks eForms.
Combina filtros estructurados (CPV, NUTS, fechas, presupuesto) con búsqueda vectorial.
Implementa el patrón de recuperación del Agentic RAG.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from pathlib import Path
import sys

# Imports de LangChain
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_chroma import Chroma

# Importar configuración y módulos propios
sys.path.append(str(Path(__file__).parent))
from config import DEFAULT_K, MIN_SIMILARITY_SCORE
from index_build import get_vectorstore

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Retriever híbrido que combina filtros estructurados con búsqueda semántica.

    Flujo de recuperación:
    1. Aplicar filtros estructurados (CPV, NUTS, fechas, presupuesto)
    2. Búsqueda vectorial sobre documentos filtrados
    3. Ranking por similaridad semántica
    4. Retornar top-k documentos
    """

    def __init__(
        self,
        vectorstore: VectorStore = None,
        k: int = None,
        min_score: float = None
    ):
        """
        Inicializa el retriever.

        Args:
            vectorstore: Vectorstore de ChromaDB (si es None, se carga automáticamente)
            k: Número de documentos a recuperar
            min_score: Umbral mínimo de similaridad
        """
        self.vectorstore = vectorstore or get_vectorstore()
        self.k = k or DEFAULT_K
        self.min_score = min_score or MIN_SIMILARITY_SCORE

    def retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        k: Optional[int] = None
    ) -> List[Document]:
        """
        Recupera documentos relevantes usando filtros + búsqueda vectorial.

        Args:
            query: Consulta en lenguaje natural
            filters: Filtros estructurados opcionales:
                - cpv_codes: List[str] o str con prefijo (ej: "7226")
                - nuts_regions: List[str] o str
                - country: str (código ISO, ej: "ESP")
                - buyer_name: str (búsqueda parcial)
                - budget_min: float
                - budget_max: float
                - deadline_from: str (YYYY-MM-DD)
                - deadline_to: str (YYYY-MM-DD)
                - publication_from: str (YYYY-MM-DD)
                - publication_to: str (YYYY-MM-DD)
                - contract_type: str
                - procedure_type: str
            k: Número de documentos a retornar (override del default)

        Returns:
            Lista de Documents ordenados por relevancia
        """
        k_fetch = (k or self.k) * 3  # Traer más para filtrar después
        filters = filters or {}

        logger.info(f"Recuperando documentos: query='{query}', k={k or self.k}, filters={filters}")

        try:
            # Búsqueda vectorial sin filtros (traemos más candidatos)
            all_results = self.vectorstore.similarity_search(
                query=query,
                k=k_fetch
            )

            # Aplicar filtros post-recuperación
            if filters:
                filtered_results = self._apply_post_filters(all_results, filters)
            else:
                filtered_results = all_results

            # Retornar top-k
            final_results = filtered_results[:k or self.k]

            logger.info(f"Recuperados {len(final_results)} documentos (de {len(all_results)} candidatos)")
            return final_results

        except Exception as e:
            logger.error(f"Error en recuperación: {e}")
            return []

    def retrieve_with_scores(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        k: Optional[int] = None
    ) -> List[tuple[Document, float]]:
        """
        Recupera documentos con sus scores de similaridad.

        Args:
            query: Consulta en lenguaje natural
            filters: Filtros estructurados
            k: Número de documentos a retornar

        Returns:
            Lista de tuplas (Document, score) ordenadas por score descendente
        """
        k_fetch = (k or self.k) * 3
        filters = filters or {}

        try:
            # Búsqueda vectorial con scores
            all_results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=k_fetch
            )

            # Filtrar por score mínimo
            score_filtered = [
                (doc, score) for doc, score in all_results
                if score >= self.min_score
            ]

            # Aplicar filtros estructurados
            if filters:
                docs_only = [doc for doc, score in score_filtered]
                filtered_docs = self._apply_post_filters(docs_only, filters)

                # Reconstruir tuplas con scores
                score_dict = {id(doc): score for doc, score in score_filtered}
                filtered_results = [
                    (doc, score_dict[id(doc)]) for doc in filtered_docs
                ]
            else:
                filtered_results = score_filtered

            # Retornar top-k
            final_results = filtered_results[:k or self.k]

            logger.info(
                f"Recuperados {len(final_results)} documentos con scores "
                f"(de {len(all_results)} candidatos, {len(score_filtered)} sobre umbral)"
            )

            return final_results

        except Exception as e:
            logger.error(f"Error en recuperación con scores: {e}")
            return []

    def _apply_post_filters(self, documents: List[Document], filters: Dict[str, Any]) -> List[Document]:
        """
        Aplica filtros post-recuperación sobre los documentos.

        Args:
            documents: Lista de documentos recuperados
            filters: Diccionario de filtros

        Returns:
            Lista filtrada de documentos
        """
        filtered_docs = []

        for doc in documents:
            metadata = doc.metadata

            # 1. Filtro por CPV codes (búsqueda de substring)
            if "cpv_codes" in filters:
                cpv_filter = filters["cpv_codes"]
                cpv_meta = metadata.get("cpv_codes", "")

                if isinstance(cpv_filter, list):
                    # Cualquier CPV que coincida
                    if not any(str(cpv) in cpv_meta for cpv in cpv_filter):
                        continue
                else:
                    # Prefijo único
                    if str(cpv_filter) not in cpv_meta:
                        continue

            # 2. Filtro por NUTS regions
            if "nuts_regions" in filters:
                nuts_filter = filters["nuts_regions"]
                nuts_meta = metadata.get("nuts_regions", "")

                if isinstance(nuts_filter, list):
                    if not any(region in nuts_meta for region in nuts_filter):
                        continue
                else:
                    if str(nuts_filter) not in nuts_meta:
                        continue

            # 3. Filtro por país
            if "country" in filters:
                country = filters["country"]
                nuts_meta = metadata.get("nuts_regions", "")
                if country not in nuts_meta:
                    continue

            # 4. Filtro por buyer_name (case-insensitive)
            if "buyer_name" in filters:
                buyer_filter = filters["buyer_name"].lower()
                buyer_meta = metadata.get("buyer_name", "").lower()
                if buyer_filter not in buyer_meta:
                    continue

            # 5. Filtro por presupuesto (rango)
            if "budget_min" in filters:
                budget = metadata.get("budget_eur")
                if budget is None or budget < filters["budget_min"]:
                    continue

            if "budget_max" in filters:
                budget = metadata.get("budget_eur")
                if budget is None or budget > filters["budget_max"]:
                    continue

            # 6. Filtro por deadline (rango de fechas)
            if "deadline_from" in filters:
                deadline = metadata.get("tender_deadline_date", "")
                if deadline < filters["deadline_from"]:
                    continue

            if "deadline_to" in filters:
                deadline = metadata.get("tender_deadline_date", "")
                if deadline > filters["deadline_to"]:
                    continue

            # 7. Filtro por fecha de publicación
            if "publication_from" in filters:
                pub_date = metadata.get("publication_date", "")
                if pub_date < filters["publication_from"]:
                    continue

            if "publication_to" in filters:
                pub_date = metadata.get("publication_date", "")
                if pub_date > filters["publication_to"]:
                    continue

            # 8. Filtro por tipo de contrato
            if "contract_type" in filters:
                contract_type = metadata.get("contract_type", "")
                if contract_type != filters["contract_type"]:
                    continue

            # 9. Filtro por tipo de procedimiento
            if "procedure_type" in filters:
                procedure_type = metadata.get("procedure_type", "")
                if procedure_type != filters["procedure_type"]:
                    continue

            # Si pasó todos los filtros, añadir al resultado
            filtered_docs.append(doc)

        return filtered_docs

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del índice.

        Returns:
            Diccionario con estadísticas
        """
        try:
            collection = self.vectorstore._collection
            count = collection.count()

            return {
                "total_documents": count,
                "collection_name": collection.name,
                "k": self.k,
                "min_score": self.min_score
            }
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}


def create_retriever(
    k: Optional[int] = None,
    min_score: Optional[float] = None
) -> HybridRetriever:
    """
    Función de conveniencia para crear un retriever.

    Args:
        k: Número de documentos a recuperar
        min_score: Umbral mínimo de similaridad

    Returns:
        Instancia de HybridRetriever
    """
    return HybridRetriever(k=k, min_score=min_score)


if __name__ == "__main__":
    # Prueba del retriever
    print("\n=== PRUEBA DEL RETRIEVER HÍBRIDO ===\n")

    # Crear retriever
    retriever = create_retriever(k=5)

    # Estadísticas
    stats = retriever.get_stats()
    print(f"Estadísticas del índice:")
    print(f"  Total documentos: {stats['total_documents']}")
    print(f"  K por defecto: {stats['k']}")
    print()

    # Prueba 1: Búsqueda sin filtros
    print("1. Búsqueda sin filtros: 'servicios SAP'")
    results = retriever.retrieve("servicios SAP", k=3)
    for i, doc in enumerate(results, 1):
        print(f"   {i}. [{doc.metadata['section']}] {doc.metadata['ojs_notice_id']}")
        print(f"      {doc.page_content[:80]}...")
    print()

    # Prueba 2: Búsqueda con filtro CPV
    print("2. Búsqueda con filtro CPV='7226': 'mantenimiento software'")
    results = retriever.retrieve(
        query="mantenimiento software",
        filters={"cpv_codes": "7226"},
        k=3
    )
    for i, doc in enumerate(results, 1):
        print(f"   {i}. [{doc.metadata['section']}] {doc.metadata['ojs_notice_id']}")
        print(f"      CPV: {doc.metadata['cpv_codes']}")
        print(f"      {doc.page_content[:80]}...")
    print()

    # Prueba 3: Búsqueda con scores
    print("3. Búsqueda con scores: 'criterios de adjudicación'")
    results_with_scores = retriever.retrieve_with_scores(
        query="criterios de adjudicación",
        k=3
    )
    for i, (doc, score) in enumerate(results_with_scores, 1):
        print(f"   {i}. Score: {score:.4f} - [{doc.metadata['section']}] {doc.metadata['ojs_notice_id']}")
        print(f"      {doc.page_content[:80]}...")
    print()

    # Prueba 4: Filtros múltiples
    print("4. Filtros múltiples (CPV + presupuesto > 500k):")
    results = retriever.retrieve(
        query="servicios informáticos",
        filters={
            "cpv_codes": "7226",
            "budget_min": 500000
        },
        k=3
    )
    for i, doc in enumerate(results, 1):
        print(f"   {i}. [{doc.metadata['section']}] {doc.metadata['ojs_notice_id']}")
        print(f"      Budget: {doc.metadata.get('budget_eur', 'N/A')} EUR")
        print(f"      {doc.page_content[:80]}...")
    print()
