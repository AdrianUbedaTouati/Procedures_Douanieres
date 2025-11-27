# -*- coding: utf-8 -*-
"""
Tools para búsqueda de licitaciones.
"""

from typing import Dict, Any, List
from .base import BaseTool
import logging

logger = logging.getLogger(__name__)


class FindBestTenderTool(BaseTool):
    """
    Encuentra LA mejor licitación (singular) usando análisis de concentración de chunks.

    Algoritmo:
    - Recupera los top 7 chunks más relevantes
    - Cuenta cuántos chunks pertenecen a cada licitación
    - Retorna la licitación con más chunks en el top 7
    - En caso de empate, usa el score más alto
    """

    name = "find_best_tender"
    description = (
        "Encuentra LA MEJOR licitación (singular) para una consulta usando análisis de concentración. "
        "**USA ESTA TOOL cuando el usuario pida 'LA mejor', 'LA más relevante', 'cuál es LA que más me conviene', "
        "'cuál me recomiendas', 'LA más interesante'.** "
        "Esta herramienta analiza los 7 chunks más relevantes y selecciona el documento con mayor concentración. "
        "Ideal para recomendaciones personalizadas donde solo se necesita UNA respuesta."
    )

    def __init__(self, retriever):
        """
        Args:
            retriever: Retriever de ChromaDB para búsqueda vectorial
        """
        super().__init__()
        self.retriever = retriever

    def run(self, query: str) -> Dict[str, Any]:
        """
        Encuentra LA mejor licitación basada en concentración de chunks.

        Args:
            query: Texto de búsqueda

        Returns:
            Dict con la mejor licitación encontrada
        """
        try:
            # 1. Recuperar top 7 chunks
            documents = self.retriever.retrieve(query=query, k=7)

            if not documents:
                return {
                    'success': True,
                    'count': 0,
                    'result': None,
                    'message': f'No se encontraron licitaciones para "{query}"'
                }

            # 2. Contar apariciones por documento
            doc_counts = {}
            doc_scores = {}
            doc_first_appearance = {}  # Para saber qué chunk apareció primero

            for idx, doc in enumerate(documents):
                meta = doc.metadata
                tender_id = meta.get('ojs_notice_id')

                if tender_id not in doc_counts:
                    doc_counts[tender_id] = 0
                    doc_scores[tender_id] = meta.get('score', 0)
                    doc_first_appearance[tender_id] = idx

                doc_counts[tender_id] += 1

            # 3. Encontrar ganador (más chunks, mejor score en empate, menor índice en doble empate)
            winner_id = max(
                doc_counts.keys(),
                key=lambda tid: (
                    doc_counts[tid],           # Prioridad 1: Más chunks
                    doc_scores[tid],           # Prioridad 2: Mejor score
                    -doc_first_appearance[tid] # Prioridad 3: Apareció primero (menos índice)
                )
            )

            # 4. Recopilar información del ganador
            winner_chunks = [doc for doc in documents if doc.metadata.get('ojs_notice_id') == winner_id]
            first_chunk = winner_chunks[0]
            meta = first_chunk.metadata

            result = {
                'id': winner_id,
                'buyer': meta.get('buyer_name', 'N/A'),
                'chunk_count': doc_counts[winner_id],
                'score': doc_scores[winner_id],
                'preview': first_chunk.page_content[:300],
                'sections_found': [doc.metadata.get('section', 'N/A') for doc in winner_chunks]
            }

            # Añadir campos opcionales
            if meta.get('budget_eur'):
                result['budget'] = float(meta.get('budget_eur'))
            if meta.get('tender_deadline_date'):
                result['deadline'] = meta.get('tender_deadline_date')
            if meta.get('cpv_codes'):
                result['cpv'] = meta.get('cpv_codes')
            if meta.get('nuts_regions'):
                result['location'] = meta.get('nuts_regions')
            if meta.get('publication_date'):
                result['published'] = meta.get('publication_date')

            return {
                'success': True,
                'count': 1,
                'result': result,
                'message': f'Licitación más relevante: {winner_id} (concentración: {doc_counts[winner_id]}/7 chunks)',
                'total_candidates': len(doc_counts),
                'algorithm': 'chunk_concentration'
            }

        except Exception as e:
            logger.error(f"Error en find_best_tender: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_schema(self) -> Dict[str, Any]:
        """Schema de la tool."""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': (
                            'La consulta del usuario. Incluye contexto sobre qué busca y por qué. '
                            'Ejemplo: "licitación de desarrollo web con presupuesto alto", '
                            '"mejor oportunidad para empresa de construcción en Madrid"'
                        )
                    }
                },
                'required': ['query']
            }
        }


class FindTopTendersTool(BaseTool):
    """
    Encuentra las X mejores licitaciones (plural) usando análisis iterativo de concentración.

    Algoritmo:
    - Recupera 7*X chunks (una ventana de 7 chunks por documento solicitado)
    - Procesa iterativamente ventanas de 7 chunks
    - En cada ventana, selecciona el documento con mayor concentración
    - Elimina todos los chunks del documento seleccionado
    - Continúa hasta obtener X documentos o quedarse sin chunks
    - Si no hay suficientes chunks, retorna menos documentos con explicación
    """

    name = "find_top_tenders"
    description = (
        "Encuentra LAS X MEJORES licitaciones (plural) usando selección iterativa por concentración. "
        "**USA ESTA TOOL cuando el usuario pida 'las mejores', 'las más relevantes', 'top 5', 'dame varias opciones', "
        "'muéstrame las más interesantes' (plural).** "
        "Analiza 7*X chunks y selecciona iterativamente los X documentos más relevantes sin repeticiones. "
        "Ideal para comparaciones, análisis de opciones múltiples, o cuando el usuario quiere ver varias alternativas."
    )

    def __init__(self, retriever):
        """
        Args:
            retriever: Retriever de ChromaDB para búsqueda vectorial
        """
        super().__init__()
        self.retriever = retriever

    def run(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Encuentra las X mejores licitaciones usando selección iterativa.

        Args:
            query: Texto de búsqueda
            limit: Número de licitaciones a retornar (default: 5)

        Returns:
            Dict con las mejores licitaciones encontradas
        """
        try:
            # 1. Calcular chunks necesarios (7 por documento)
            k_chunks = limit * 7

            # 2. Recuperar todos los chunks en una sola consulta
            all_docs = self.retriever.retrieve(query=query, k=k_chunks)

            if not all_docs:
                return {
                    'success': True,
                    'count': 0,
                    'requested': limit,
                    'results': [],
                    'message': f'No se encontraron licitaciones para "{query}"'
                }

            # Verificar si hay suficientes chunks (mínimo 7)
            if len(all_docs) < 7:
                return {
                    'success': True,
                    'count': 0,
                    'requested': limit,
                    'results': [],
                    'message': f'Insuficientes chunks para análisis (encontrados: {len(all_docs)}, necesarios: 7 mínimo)',
                    'total_chunks_found': len(all_docs)
                }

            # 3. Selección iterativa
            selected_tenders = []
            used_tender_ids = set()
            available_chunks = list(all_docs)  # Copia para ir eliminando

            iteration = 0
            while len(selected_tenders) < limit and len(available_chunks) >= 7:
                iteration += 1

                # Tomar ventana de 7 chunks
                window = available_chunks[:7]

                # Contar en esta ventana (solo documentos NO usados)
                window_counts = {}
                window_scores = {}
                window_first_idx = {}

                for idx, doc in enumerate(window):
                    tender_id = doc.metadata.get('ojs_notice_id')

                    # Solo contar si no está ya seleccionado
                    if tender_id not in used_tender_ids:
                        if tender_id not in window_counts:
                            window_counts[tender_id] = 0
                            window_scores[tender_id] = doc.metadata.get('score', 0)
                            window_first_idx[tender_id] = idx

                        window_counts[tender_id] += 1

                # Si no hay documentos nuevos en esta ventana, terminamos
                if not window_counts:
                    logger.info(f"Iteración {iteration}: No hay documentos nuevos en ventana, terminando")
                    break

                # Encontrar ganador en esta ventana
                winner_id = max(
                    window_counts.keys(),
                    key=lambda tid: (
                        window_counts[tid],
                        window_scores[tid],
                        -window_first_idx[tid]
                    )
                )

                # Recopilar información del ganador
                winner_chunks = [doc for doc in all_docs if doc.metadata.get('ojs_notice_id') == winner_id]
                first_chunk = winner_chunks[0]
                meta = first_chunk.metadata

                result = {
                    'id': winner_id,
                    'buyer': meta.get('buyer_name', 'N/A'),
                    'chunk_count': len(winner_chunks),
                    'score': window_scores[winner_id],
                    'preview': first_chunk.page_content[:200],
                    'rank': len(selected_tenders) + 1
                }

                # Campos opcionales
                if meta.get('budget_eur'):
                    result['budget'] = float(meta.get('budget_eur'))
                if meta.get('tender_deadline_date'):
                    result['deadline'] = meta.get('tender_deadline_date')
                if meta.get('cpv_codes'):
                    result['cpv'] = meta.get('cpv_codes')
                if meta.get('nuts_regions'):
                    result['location'] = meta.get('nuts_regions')
                if meta.get('publication_date'):
                    result['published'] = meta.get('publication_date')

                selected_tenders.append(result)
                used_tender_ids.add(winner_id)

                # Eliminar TODOS los chunks del ganador de available_chunks
                available_chunks = [
                    doc for doc in available_chunks
                    if doc.metadata.get('ojs_notice_id') != winner_id
                ]

                logger.info(f"Iteración {iteration}: Seleccionado {winner_id} (concentración: {window_counts[winner_id]}/7), quedan {len(available_chunks)} chunks")

            # 4. Construir mensaje de resultado
            found_count = len(selected_tenders)

            if found_count < limit:
                message = (
                    f'Encontradas {found_count} licitaciones de las {limit} solicitadas. '
                    f'Disponibilidad limitada de chunks (total recuperado: {len(all_docs)} chunks).'
                )
            else:
                message = f'Encontradas las {found_count} mejores licitaciones para "{query}"'

            return {
                'success': True,
                'count': found_count,
                'requested': limit,
                'results': selected_tenders,
                'message': message,
                'total_chunks_analyzed': len(all_docs),
                'iterations': iteration,
                'algorithm': 'iterative_chunk_concentration'
            }

        except Exception as e:
            logger.error(f"Error en find_top_tenders: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_schema(self) -> Dict[str, Any]:
        """Schema de la tool."""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': (
                            'La consulta del usuario. Incluye contexto sobre qué busca. '
                            'Ejemplo: "licitaciones de software", "oportunidades en construcción", '
                            '"servicios de consultoría en Madrid"'
                        )
                    },
                    'limit': {
                        'type': 'integer',
                        'description': (
                            'Número de licitaciones a devolver. Ajusta según la necesidad: '
                            '3-5 para comparaciones rápidas, 10-15 para análisis amplios. Por defecto: 5'
                        ),
                        'default': 5,
                        'minimum': 1,
                        'maximum': 20
                    }
                },
                'required': ['query']
            }
        }


class FindByBudgetTool(BaseTool):
    """
    Busca licitaciones por rango de presupuesto.
    """

    name = "find_by_budget"
    description = "Busca licitaciones por presupuesto/dinero. Usa esta función cuando el usuario mencione CANTIDADES DE DINERO, presupuesto, o quiera licitaciones caras/baratas. Ejemplos: 'con más de 500k euros', 'la más cara', 'menos de un millón'. Devuelve las licitaciones ordenadas por presupuesto de mayor a menor."

    def __init__(self, db_session=None):
        """
        Args:
            db_session: Sesión de base de datos Django (opcional, usa default si no se pasa)
        """
        super().__init__()
        self.db_session = db_session

    def run(self, min_euros: float = None, max_euros: float = None, limit: int = 10) -> Dict[str, Any]:
        """
        Busca licitaciones por presupuesto.

        Args:
            min_euros: Presupuesto mínimo en EUR
            max_euros: Presupuesto máximo en EUR
            limit: Número máximo de resultados

        Returns:
            Dict con resultados ordenados por presupuesto DESC
        """
        try:
            # Importar aquí para evitar circular imports
            import sys
            from pathlib import Path
            import django

            # Setup Django si no está configurado
            if not django.apps.apps.ready:
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                import os
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
                django.setup()

            from apps.tenders.models import Tender

            # Query a la base de datos - construir filtro dinámicamente
            queryset = Tender.objects.exclude(budget_amount__isnull=True)

            # Aplicar filtros solo si se proporcionan
            if min_euros is not None:
                queryset = queryset.filter(budget_amount__gte=min_euros)
            if max_euros is not None:
                queryset = queryset.filter(budget_amount__lte=max_euros)

            # Ordenar y limitar
            tenders = queryset.order_by('-budget_amount')[:limit]

            if not tenders.exists():
                return {
                    'success': True,
                    'count': 0,
                    'results': [],
                    'message': f'No se encontraron licitaciones con los criterios de presupuesto especificados'
                }

            # Formatear resultados
            results = []
            for tender in tenders:
                result = {
                    'id': tender.ojs_notice_id,
                    'title': tender.title,
                    'budget': float(tender.budget_amount),
                    'currency': tender.currency,
                    'buyer': tender.buyer_name,
                }

                # Campos opcionales
                if tender.deadline:
                    result['deadline'] = tender.deadline.isoformat()
                if tender.publication_date:
                    result['published'] = tender.publication_date.isoformat()
                if tender.cpv_codes:
                    result['cpv'] = tender.cpv_codes
                if tender.contract_type:
                    result['contract_type'] = tender.contract_type

                results.append(result)

            # Construir mensaje informativo
            msg_parts = [f'Encontradas {len(results)} licitaciones']
            if min_euros is not None:
                msg_parts.append(f'presupuesto mínimo {min_euros}€')
            if max_euros is not None:
                msg_parts.append(f'presupuesto máximo {max_euros}€')

            return {
                'success': True,
                'count': len(results),
                'results': results,
                'message': ' con '.join(msg_parts) if len(msg_parts) > 1 else msg_parts[0]
            }

        except Exception as e:
            logger.error(f"Error en find_by_budget: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_schema(self) -> Dict[str, Any]:
        """Schema de la tool."""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'min_euros': {
                        'type': 'number',
                        'description': 'Presupuesto mínimo en euros. Si el usuario dice "más de 100k", pon 100000 aquí. Si no menciona mínimo, NO uses este parámetro'
                    },
                    'max_euros': {
                        'type': 'number',
                        'description': 'Presupuesto máximo en euros. Si el usuario dice "menos de 500k", pon 500000 aquí. Si no menciona máximo, NO uses este parámetro'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Número de licitaciones a devolver. Ajusta según la necesidad: usa 10-15 para búsquedas estándar, 30-50 para análisis exhaustivos. Por defecto: 10',
                        'default': 10,
                        'minimum': 1,
                        'maximum': 100
                    }
                }
            }
        }


class FindByDeadlineTool(BaseTool):
    """
    Busca licitaciones por fecha límite de presentación.
    """

    name = "find_by_deadline"
    description = "Busca licitaciones por fecha límite de presentación. Usa esta función cuando el usuario pregunte por licitaciones que vencen pronto, que tienen deadline en un rango de fechas específico, o que ya vencieron. Ejemplo: 'licitaciones que vencen esta semana', 'con deadline antes del 15 de marzo'."

    def __init__(self, db_session=None):
        """
        Args:
            db_session: Sesión de base de datos Django (opcional)
        """
        super().__init__()
        self.db_session = db_session

    def run(self, date_from: str = None, date_to: str = None, limit: int = 10) -> Dict[str, Any]:
        """
        Busca licitaciones por fecha límite.

        Args:
            date_from: Fecha inicial en formato YYYY-MM-DD (opcional)
            date_to: Fecha final en formato YYYY-MM-DD (opcional)
            limit: Número de resultados

        Returns:
            Dict con resultados de la búsqueda
        """
        try:
            # Setup Django si es necesario
            import django
            if not django.apps.apps.ready:
                import os
                import sys
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
                django.setup()

            from apps.tenders.models import Tender
            from datetime import datetime

            # Query a la base de datos - construir filtro dinámicamente
            queryset = Tender.objects.exclude(tender_deadline_date__isnull=True)

            # Aplicar filtros de fecha
            if date_from:
                queryset = queryset.filter(tender_deadline_date__gte=date_from)
            if date_to:
                queryset = queryset.filter(tender_deadline_date__lte=date_to)

            # Ordenar por fecha (más próximas primero)
            tenders = queryset.order_by('tender_deadline_date')[:limit]

            if not tenders.exists():
                return {
                    'success': True,
                    'count': 0,
                    'results': [],
                    'message': 'No se encontraron licitaciones con los criterios de fecha especificados'
                }

            # Formatear resultados
            results = []
            for tender in tenders:
                result = {
                    'id': tender.ojs_notice_id,
                    'title': tender.title,
                    'buyer': tender.buyer_name,
                    'deadline_date': tender.tender_deadline_date.isoformat() if tender.tender_deadline_date else None
                }

                # Añadir información opcional
                if tender.tender_deadline_time:
                    result['deadline_time'] = tender.tender_deadline_time.isoformat()

                if tender.budget_amount:
                    result['budget'] = float(tender.budget_amount)
                    result['currency'] = tender.currency or 'EUR'

                if tender.cpv_codes:
                    result['cpv_codes'] = tender.cpv_codes

                if tender.contract_type:
                    result['contract_type'] = tender.contract_type

                # Calcular días restantes
                if tender.tender_deadline_date:
                    from datetime import date
                    today = date.today()
                    days_left = (tender.tender_deadline_date - today).days
                    result['days_remaining'] = days_left
                    if days_left < 0:
                        result['status'] = 'expired'
                    elif days_left <= 7:
                        result['status'] = 'urgent'
                    elif days_left <= 30:
                        result['status'] = 'soon'
                    else:
                        result['status'] = 'open'

                results.append(result)

            # Construir mensaje informativo
            msg_parts = [f'Encontradas {len(results)} licitaciones']
            if date_from:
                msg_parts.append(f'desde {date_from}')
            if date_to:
                msg_parts.append(f'hasta {date_to}')

            return {
                'success': True,
                'count': len(results),
                'results': results,
                'message': ' '.join(msg_parts)
            }

        except Exception as e:
            logger.error(f"Error en find_by_deadline: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_schema(self) -> Dict[str, Any]:
        """Retorna el schema de la tool en formato OpenAI Function Calling."""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'date_from': {
                        'type': 'string',
                        'description': 'Fecha inicial en formato YYYY-MM-DD. Ejemplo: "2025-01-20". Si el usuario dice "desde mañana", calcula la fecha y úsala aquí'
                    },
                    'date_to': {
                        'type': 'string',
                        'description': 'Fecha final en formato YYYY-MM-DD. Ejemplo: "2025-02-15". Si el usuario dice "hasta fin de mes", calcula la fecha y úsala aquí'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Número de licitaciones a devolver ordenadas por proximidad de deadline. Ajusta según necesidad: 10 para urgentes, 30+ para planificación amplia. Por defecto: 10',
                        'default': 10,
                        'minimum': 1,
                        'maximum': 100
                    }
                }
            }
        }


class FindByCPVTool(BaseTool):
    """
    Busca licitaciones por código CPV (sector/tipo de contrato).
    """

    name = "find_by_cpv"
    description = "Busca licitaciones por código CPV (Common Procurement Vocabulary) que clasifica el tipo de contrato o sector. Usa esta función cuando el usuario busque por sector específico o tipo de servicio/producto. Los códigos CPV son jerárquicos: '72' para IT, '45' para construcción, '80' para educación, etc."

    def __init__(self, retriever=None):
        """
        Args:
            retriever: HybridRetriever con soporte de filtros
        """
        super().__init__()
        self.retriever = retriever

    def run(self, cpv_code: str, limit: int = 10) -> Dict[str, Any]:
        """
        Busca licitaciones por código CPV.

        Args:
            cpv_code: Código CPV (puede ser prefijo). Ej: "72" para IT, "45" para construcción
            limit: Número de resultados

        Returns:
            Dict con resultados de la búsqueda
        """
        try:
            if not self.retriever:
                return {
                    'success': False,
                    'error': 'Retriever no inicializado'
                }

            # Buscar usando el retriever con filtro CPV
            # El retriever hace búsqueda de substring, así que un prefijo funciona
            filters = {'cpv_codes': cpv_code}

            # Hacer búsqueda genérica pero filtrada por CPV
            documents = self.retriever.retrieve(
                query=f"licitaciones sector CPV {cpv_code}",
                filters=filters,
                k=limit
            )

            if not documents:
                return {
                    'success': True,
                    'count': 0,
                    'results': [],
                    'message': f'No se encontraron licitaciones con código CPV que contenga "{cpv_code}"'
                }

            # Formatear resultados
            results = []
            seen_ids = set()

            for doc in documents:
                meta = doc.metadata
                tender_id = meta.get('ojs_notice_id')

                if tender_id in seen_ids:
                    continue
                seen_ids.add(tender_id)

                result = {
                    'id': tender_id,
                    'section': meta.get('section', 'N/A'),
                    'buyer': meta.get('buyer_name', 'N/A'),
                    'cpv_codes': meta.get('cpv_codes', 'N/A'),
                    'preview': doc.page_content[:200]
                }

                # Añadir campos opcionales
                if meta.get('budget_eur'):
                    result['budget'] = float(meta.get('budget_eur'))

                if meta.get('tender_deadline_date'):
                    result['deadline'] = meta.get('tender_deadline_date')

                if meta.get('nuts_regions'):
                    result['location'] = meta.get('nuts_regions')

                results.append(result)

            return {
                'success': True,
                'count': len(results),
                'cpv_filter': cpv_code,
                'results': results,
                'message': f'Encontradas {len(results)} licitaciones con CPV que contiene "{cpv_code}"'
            }

        except Exception as e:
            logger.error(f"Error en find_by_cpv: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_schema(self) -> Dict[str, Any]:
        """Retorna el schema de la tool en formato OpenAI Function Calling."""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'cpv_code': {
                        'type': 'string',
                        'description': 'Código CPV o prefijo. Ejemplos: "72" para IT/software, "45" para construcción, "80" para educación, "85" para salud. Puede ser un código completo o solo los primeros dígitos'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Número de licitaciones a devolver filtradas por CPV. Ajusta según análisis: 10-15 para sectores específicos, 30+ para análisis de mercado amplio. Por defecto: 10',
                        'default': 10,
                        'minimum': 1,
                        'maximum': 100
                    }
                },
                'required': ['cpv_code']
            }
        }


class FindByLocationTool(BaseTool):
    """
    Busca licitaciones por ubicación geográfica (códigos NUTS).
    """

    name = "find_by_location"
    description = "Busca licitaciones por ubicación geográfica usando códigos NUTS. Usa esta función cuando el usuario busque licitaciones en una región, ciudad, o país específico. Ejemplos: 'Madrid', 'Cataluña', 'España'. Los códigos NUTS son jerárquicos: 'ES' (España), 'ES3' (Madrid), 'ES51' (Cataluña)."

    def __init__(self, retriever=None):
        """
        Args:
            retriever: HybridRetriever con soporte de filtros
        """
        super().__init__()
        self.retriever = retriever

    def run(self, location: str, limit: int = 10) -> Dict[str, Any]:
        """
        Busca licitaciones por ubicación.

        Args:
            location: Código NUTS o nombre de región/ciudad. Ej: "ES3" para Madrid, "ES" para España
            limit: Número de resultados

        Returns:
            Dict con resultados de la búsqueda
        """
        try:
            if not self.retriever:
                return {
                    'success': False,
                    'error': 'Retriever no inicializado'
                }

            # Normalizar ubicación a código NUTS si es posible
            # Mapeo común de nombres a códigos NUTS
            location_map = {
                'españa': 'ES',
                'spain': 'ES',
                'madrid': 'ES3',
                'cataluña': 'ES51',
                'catalunya': 'ES51',
                'barcelona': 'ES51',
                'valencia': 'ES52',
                'andalucia': 'ES6',
                'andalucía': 'ES6',
                'pais vasco': 'ES2',
                'país vasco': 'ES2',
                'galicia': 'ES11'
            }

            search_code = location_map.get(location.lower(), location.upper())

            # Buscar usando el retriever con filtro NUTS
            filters = {'nuts_regions': search_code}

            # Hacer búsqueda genérica pero filtrada por ubicación
            documents = self.retriever.retrieve(
                query=f"licitaciones ubicación {location}",
                filters=filters,
                k=limit
            )

            if not documents:
                return {
                    'success': True,
                    'count': 0,
                    'results': [],
                    'message': f'No se encontraron licitaciones en la ubicación "{location}" (código NUTS: {search_code})'
                }

            # Formatear resultados
            results = []
            seen_ids = set()

            for doc in documents:
                meta = doc.metadata
                tender_id = meta.get('ojs_notice_id')

                if tender_id in seen_ids:
                    continue
                seen_ids.add(tender_id)

                result = {
                    'id': tender_id,
                    'section': meta.get('section', 'N/A'),
                    'buyer': meta.get('buyer_name', 'N/A'),
                    'location': meta.get('nuts_regions', 'N/A'),
                    'preview': doc.page_content[:200]
                }

                # Añadir campos opcionales
                if meta.get('budget_eur'):
                    result['budget'] = float(meta.get('budget_eur'))

                if meta.get('tender_deadline_date'):
                    result['deadline'] = meta.get('tender_deadline_date')

                if meta.get('cpv_codes'):
                    result['cpv_codes'] = meta.get('cpv_codes')

                results.append(result)

            return {
                'success': True,
                'count': len(results),
                'location_filter': search_code,
                'results': results,
                'message': f'Encontradas {len(results)} licitaciones en "{location}" (NUTS: {search_code})'
            }

        except Exception as e:
            logger.error(f"Error en find_by_location: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_schema(self) -> Dict[str, Any]:
        """Retorna el schema de la tool en formato OpenAI Function Calling."""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'location': {
                        'type': 'string',
                        'description': 'Ubicación o código NUTS. Puede ser nombre de región (ej: "Madrid", "Cataluña", "España") o código NUTS directo (ej: "ES3", "ES51"). Para toda España usa "ES"'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Número de licitaciones a devolver filtradas por ubicación. Ajusta según análisis: 10-15 para regiones específicas, 30+ para análisis territorial amplio. Por defecto: 10',
                        'default': 10,
                        'minimum': 1,
                        'maximum': 100
                    }
                },
                'required': ['location']
            }
        }


class GetStatisticsTool(BaseTool):
    """
    Obtiene estadísticas agregadas sobre licitaciones.
    """

    name = "get_statistics"
    description = "Obtiene estadísticas y análisis agregados sobre licitaciones. Usa esta función cuando el usuario pregunte por números, totales, promedios, o quiera un resumen general. Ejemplos: '¿cuántas licitaciones hay?', 'presupuesto promedio', 'sectores más comunes'."

    def __init__(self, db_session=None):
        """
        Args:
            db_session: Sesión de base de datos Django (opcional)
        """
        super().__init__()
        self.db_session = db_session

    def run(self, stat_type: str = 'general') -> Dict[str, Any]:
        """
        Obtiene estadísticas.

        Args:
            stat_type: Tipo de estadística: 'general', 'budget', 'deadline', 'cpv', 'location'

        Returns:
            Dict con estadísticas
        """
        try:
            # Setup Django si es necesario
            import django
            if not django.apps.apps.ready:
                import os
                import sys
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
                django.setup()

            from apps.tenders.models import Tender
            from django.db.models import Count, Avg, Sum, Min, Max
            from datetime import date, timedelta

            stats = {}

            if stat_type in ['general', 'all']:
                # Estadísticas generales
                total_tenders = Tender.objects.count()
                stats['total_tenders'] = total_tenders

                # Con deadline futuro
                active_tenders = Tender.objects.filter(
                    tender_deadline_date__gte=date.today()
                ).count()
                stats['active_tenders'] = active_tenders

                # Por tipo de contrato
                contract_types = Tender.objects.values('contract_type').annotate(
                    count=Count('id')
                ).order_by('-count')[:5]
                stats['top_contract_types'] = list(contract_types)

            if stat_type in ['budget', 'all']:
                # Estadísticas de presupuesto
                budget_stats = Tender.objects.exclude(
                    budget_amount__isnull=True
                ).aggregate(
                    avg_budget=Avg('budget_amount'),
                    total_budget=Sum('budget_amount'),
                    min_budget=Min('budget_amount'),
                    max_budget=Max('budget_amount'),
                    count=Count('id')
                )
                stats['budget'] = {
                    'count': budget_stats['count'],
                    'average': float(budget_stats['avg_budget'] or 0),
                    'total': float(budget_stats['total_budget'] or 0),
                    'min': float(budget_stats['min_budget'] or 0),
                    'max': float(budget_stats['max_budget'] or 0)
                }

            if stat_type in ['deadline', 'all']:
                # Estadísticas de deadline
                today = date.today()

                urgent = Tender.objects.filter(
                    tender_deadline_date__gte=today,
                    tender_deadline_date__lte=today + timedelta(days=7)
                ).count()

                soon = Tender.objects.filter(
                    tender_deadline_date__gt=today + timedelta(days=7),
                    tender_deadline_date__lte=today + timedelta(days=30)
                ).count()

                later = Tender.objects.filter(
                    tender_deadline_date__gt=today + timedelta(days=30)
                ).count()

                stats['deadlines'] = {
                    'urgent': urgent,  # <7 días
                    'soon': soon,      # 7-30 días
                    'later': later     # >30 días
                }

            if stat_type in ['cpv', 'all']:
                # Top sectores CPV (aproximado - cuenta licitaciones con ese prefijo)
                # Nota: Como cpv_codes es un campo de texto, hacemos análisis simple
                tenders_with_cpv = Tender.objects.exclude(cpv_codes__isnull=True).exclude(cpv_codes='')

                cpv_counts = {}
                for tender in tenders_with_cpv[:200]:  # Limitar para performance
                    if tender.cpv_codes:
                        # Extraer primer código CPV (primeros 2 dígitos)
                        codes = tender.cpv_codes.split(',')
                        if codes and len(codes[0]) >= 2:
                            prefix = codes[0][:2].strip()
                            cpv_counts[prefix] = cpv_counts.get(prefix, 0) + 1

                # Top 5 CPV
                top_cpv = sorted(cpv_counts.items(), key=lambda x: x[1], reverse=True)[:5]

                # Mapeo de códigos CPV a nombres
                cpv_names = {
                    '45': 'Construcción',
                    '72': 'IT/Tecnología',
                    '80': 'Educación',
                    '85': 'Salud',
                    '90': 'Saneamiento/Medio Ambiente',
                    '71': 'Servicios de Ingeniería',
                    '79': 'Servicios Empresariales'
                }

                stats['top_cpv_sectors'] = [
                    {'code': code, 'name': cpv_names.get(code, 'Otros'), 'count': count}
                    for code, count in top_cpv
                ]

            if stat_type in ['location', 'all']:
                # Top ubicaciones NUTS
                tenders_with_nuts = Tender.objects.exclude(nuts_regions__isnull=True).exclude(nuts_regions='')

                nuts_counts = {}
                for tender in tenders_with_nuts[:200]:  # Limitar para performance
                    if tender.nuts_regions:
                        # Extraer primer código NUTS (país)
                        codes = tender.nuts_regions.split(',')
                        if codes:
                            country = codes[0][:2].strip()
                            nuts_counts[country] = nuts_counts.get(country, 0) + 1

                top_locations = sorted(nuts_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                stats['top_locations'] = [
                    {'code': code, 'count': count}
                    for code, count in top_locations
                ]

            return {
                'success': True,
                'stat_type': stat_type,
                'statistics': stats,
                'generated_at': date.today().isoformat()
            }

        except Exception as e:
            logger.error(f"Error en get_statistics: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_schema(self) -> Dict[str, Any]:
        """Retorna el schema de la tool en formato OpenAI Function Calling."""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'stat_type': {
                        'type': 'string',
                        'enum': ['general', 'budget', 'deadline', 'cpv', 'location', 'all'],
                        'description': 'Tipo de estadística: "general" para totales, "budget" para presupuestos, "deadline" para fechas, "cpv" para sectores, "location" para ubicaciones, "all" para todo',
                        'default': 'general'
                    }
                }
            }
        }
