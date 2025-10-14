"""
Service layer for integrating Agent_IA recommendation engine with Tenders
"""
import os
import sys
from typing import List, Dict, Any
from django.conf import settings

# Add agent_ia_core to Python path
agent_ia_path = os.path.join(settings.BASE_DIR, 'agent_ia_core')
if agent_ia_path not in sys.path:
    sys.path.insert(0, agent_ia_path)


class TenderRecommendationService:
    """Service to generate tender recommendations using Agent_IA"""

    def __init__(self, user):
        """
        Initialize the recommendation service

        Args:
            user: Django User instance with company_profile
        """
        self.user = user
        self.api_key = user.llm_api_key

    def generate_recommendations(self, tenders_queryset) -> List[Dict[str, Any]]:
        """
        Generate recommendations for a set of tenders based on company profile

        Args:
            tenders_queryset: QuerySet of Tender objects to evaluate

        Returns:
            List of dicts with recommendation data
        """
        if not self.api_key:
            raise ValueError("Usuario debe tener API key configurada")

        try:
            # Get company profile
            company_profile = self.user.company_profile
            if not company_profile.is_complete:
                raise ValueError("El perfil de empresa debe estar completo")

            # Convert profile to agent format
            empresa_dict = company_profile.to_agent_format()

            # Import recommendation engine
            from recommendation_engine import RecommendationEngine

            # Set API key in environment
            original_key = os.environ.get('GOOGLE_API_KEY')
            if self.api_key:
                os.environ['GOOGLE_API_KEY'] = self.api_key

            try:
                # Initialize engine
                engine = RecommendationEngine()

                recommendations = []

                # Process each tender
                for tender in tenders_queryset:
                    # Convert tender to dict format expected by engine
                    licitacion_dict = self._tender_to_dict(tender)

                    # Generate recommendation
                    try:
                        rec = engine.evaluar_licitacion(licitacion_dict, empresa_dict)

                        recommendations.append({
                            'tender': tender,
                            'score_total': rec['score_total'],
                            'score_technical': rec['score_tecnico'],
                            'score_budget': rec['score_presupuesto'],
                            'score_geographic': rec['score_geografico'],
                            'score_experience': rec['score_experiencia'],
                            'score_competition': rec['score_competencia'],
                            'probability_success': rec['probabilidad_exito'],
                            'recommendation_level': rec['nivel_recomendacion'],
                            'match_reasons': rec.get('razones_match', []),
                            'warning_factors': rec.get('factores_advertencia', []),
                            'contact_info': rec.get('informacion_contacto', {})
                        })
                    except Exception as e:
                        # Log error but continue with other tenders
                        print(f"Error evaluating tender {tender.ojs_notice_id}: {e}")
                        continue

                return recommendations

            finally:
                # Restore original key
                if original_key:
                    os.environ['GOOGLE_API_KEY'] = original_key
                elif 'GOOGLE_API_KEY' in os.environ:
                    del os.environ['GOOGLE_API_KEY']

        except ImportError as e:
            raise Exception(f"Error importing recommendation engine: {e}")
        except Exception as e:
            raise Exception(f"Error generating recommendations: {e}")

    def _tender_to_dict(self, tender) -> Dict[str, Any]:
        """
        Convert a Tender model instance to dict format expected by recommendation engine

        Args:
            tender: Tender model instance

        Returns:
            Dict with tender data
        """
        return {
            'ojs_notice_id': tender.ojs_notice_id,
            'title': tender.title,
            'description': tender.description,
            'short_description': tender.short_description,
            'cpv_codes': tender.cpv_codes or [],
            'nuts_regions': tender.nuts_regions or [],
            'budget_amount': float(tender.budget_amount) if tender.budget_amount else None,
            'currency': tender.currency,
            'buyer_name': tender.buyer_name,
            'buyer_type': tender.buyer_type,
            'contract_type': tender.contract_type,
            'procedure_type': tender.procedure_type,
            'award_criteria': tender.award_criteria,
            'deadline': tender.deadline.isoformat() if tender.deadline else None,
            'publication_date': tender.publication_date.isoformat() if tender.publication_date else None,
            'contact_email': tender.contact_email,
            'contact_phone': tender.contact_phone,
            'contact_url': tender.contact_url,
        }

    def evaluate_single_tender(self, tender) -> Dict[str, Any]:
        """
        Evaluate a single tender and return recommendation

        Args:
            tender: Tender model instance

        Returns:
            Dict with recommendation data
        """
        recommendations = self.generate_recommendations([tender])
        return recommendations[0] if recommendations else None


class TenderIndexingService:
    """Service to index tenders into ChromaDB for RAG"""

    def __init__(self, user):
        """
        Initialize the indexing service

        Args:
            user: Django User instance with API key
        """
        self.user = user
        self.api_key = user.llm_api_key

    def index_tender(self, tender) -> bool:
        """
        Index a single tender into ChromaDB

        Args:
            tender: Tender model instance

        Returns:
            bool: True if successful
        """
        if not self.api_key:
            raise ValueError("Usuario debe tener API key configurada")

        try:
            from chunking import chunk_tender_document
            from config import get_chroma_client

            # Set API key
            original_key = os.environ.get('GOOGLE_API_KEY')
            if self.api_key:
                os.environ['GOOGLE_API_KEY'] = self.api_key

            try:
                # Get ChromaDB client
                client = get_chroma_client()
                collection = client.get_or_create_collection(
                    name=settings.CHROMA_COLLECTION_NAME or "licitaciones"
                )

                # Prepare document
                document = {
                    'ojs_notice_id': tender.ojs_notice_id,
                    'title': tender.title,
                    'description': tender.description,
                    'cpv_codes': tender.cpv_codes,
                    'nuts_regions': tender.nuts_regions,
                    'budget_amount': float(tender.budget_amount) if tender.budget_amount else None,
                    'buyer_name': tender.buyer_name,
                    'deadline': tender.deadline.isoformat() if tender.deadline else None,
                }

                # Chunk the document
                chunks = chunk_tender_document(document)

                # Add to collection
                for i, chunk in enumerate(chunks):
                    collection.add(
                        documents=[chunk['text']],
                        metadatas=[chunk['metadata']],
                        ids=[f"{tender.ojs_notice_id}_chunk_{i}"]
                    )

                # Update indexed_at timestamp
                from django.utils import timezone
                tender.indexed_at = timezone.now()
                tender.save(update_fields=['indexed_at'])

                return True

            finally:
                # Restore original key
                if original_key:
                    os.environ['GOOGLE_API_KEY'] = original_key
                elif 'GOOGLE_API_KEY' in os.environ:
                    del os.environ['GOOGLE_API_KEY']

        except Exception as e:
            print(f"Error indexing tender {tender.ojs_notice_id}: {e}")
            return False

    def bulk_index_tenders(self, tenders_queryset) -> Dict[str, int]:
        """
        Index multiple tenders

        Args:
            tenders_queryset: QuerySet of Tender objects

        Returns:
            Dict with success/failure counts
        """
        success_count = 0
        failure_count = 0

        for tender in tenders_queryset:
            try:
                if self.index_tender(tender):
                    success_count += 1
                else:
                    failure_count += 1
            except Exception:
                failure_count += 1

        return {
            'success': success_count,
            'failure': failure_count,
            'total': success_count + failure_count
        }
