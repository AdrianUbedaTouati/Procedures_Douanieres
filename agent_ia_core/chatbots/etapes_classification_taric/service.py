"""
Service pour le chatbot de classification TARIC.
Reutilise ChatAgentService avec des prompts et tools specialises.
"""
import json
import re
import sys
from typing import Dict, Any, List, Optional

from .config import CHATBOT_CONFIG
from .prompts import (
    TARIC_SYSTEM_PROMPT,
    TARIC_WELCOME_MESSAGE,
    TARIC_ANALYSIS_PROMPT,
    TARIC_VALIDATION_MESSAGE
)


class TARICClassificationService:
    """
    Service specialise pour la classification TARIC.
    Encapsule la logique du chatbot de classification.
    """

    def __init__(self, user, expedition):
        """
        Initialise le service de classification TARIC.

        Args:
            user: Django User instance
            expedition: Expedition instance
        """
        self.user = user
        self.expedition = expedition
        self._chat_service = None

    def _get_chat_service(self):
        """Obtenir le service de chat sous-jacent."""
        if self._chat_service is None:
            from apps.chat.services import ChatAgentService
            self._chat_service = ChatAgentService(self.user)
        return self._chat_service

    def get_welcome_message(self) -> Dict[str, Any]:
        """
        Retourne le message de bienvenue du chatbot.

        Returns:
            Dict avec content et metadata
        """
        return {
            'content': TARIC_WELCOME_MESSAGE,
            'metadata': {
                'type': 'welcome',
                'tools_used': [],
                'proposals': None
            }
        }

    def get_expedition_documents_info(self) -> Dict[str, Any]:
        """
        Recupere les informations sur les documents de l'expedition.

        Returns:
            Dict avec photos et fiches_techniques
        """
        photos = list(self.expedition.documents.filter(type='photo').values(
            'id', 'nom_original', 'fichier', 'created_at'
        ))
        fiches = list(self.expedition.documents.filter(type='fiche_technique').values(
            'id', 'nom_original', 'fichier', 'created_at'
        ))

        return {
            'photos': photos,
            'fiches_techniques': fiches,
            'total': len(photos) + len(fiches),
            'has_photos': len(photos) > 0,
            'has_fiches': len(fiches) > 0
        }

    def process_message(self, message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Traite un message utilisateur.

        Args:
            message: Message de l'utilisateur
            conversation_history: Historique de la conversation

        Returns:
            Dict avec content, metadata et proposals (si applicable)
        """
        try:
            # Preparer l'historique avec le system prompt TARIC
            history = conversation_history or []

            # Ajouter contexte de l'expedition
            expedition_context = self._build_expedition_context()

            # Construire le message enrichi
            enriched_message = f"""{message}

[CONTEXTE EXPEDITION]
{expedition_context}
"""

            # Appeler le service de chat
            chat_service = self._get_chat_service()
            result = chat_service.process_message(enriched_message, history)

            # Analyser la reponse pour extraire les proposals
            proposals = self._extract_proposals(result['content'])

            # Ajouter les proposals au metadata
            result['metadata']['proposals'] = proposals
            result['metadata']['has_proposals'] = proposals is not None and len(proposals) > 0

            # Si des proposals ont ete detectes, nettoyer le contenu
            if proposals:
                result['content'] = self._format_response_with_proposals(result['content'], proposals)

            return result

        except Exception as e:
            print(f"[TARIC_SERVICE] Erreur: {e}", file=sys.stderr)
            return {
                'content': f"Desole, une erreur s'est produite: {str(e)}",
                'metadata': {
                    'error': str(e),
                    'type': 'error',
                    'proposals': None
                }
            }

    def _build_expedition_context(self) -> str:
        """Construit le contexte de l'expedition pour le prompt."""
        docs = self.get_expedition_documents_info()

        context_parts = [
            f"Reference: {self.expedition.reference}",
            f"Produit: {self.expedition.nom_article or 'Non specifie'}",
        ]

        if docs['has_photos']:
            photo_names = [p['nom_original'] for p in docs['photos']]
            context_parts.append(f"Photos disponibles: {', '.join(photo_names)}")

        if docs['has_fiches']:
            fiche_names = [f['nom_original'] for f in docs['fiches_techniques']]
            context_parts.append(f"Fiches techniques: {', '.join(fiche_names)}")

        if not docs['has_photos'] and not docs['has_fiches']:
            context_parts.append("Aucun document telecharge pour le moment.")

        return '\n'.join(context_parts)

    def _extract_proposals(self, content: str) -> Optional[List[Dict]]:
        """
        Extrait les propositions de codes TARIC de la reponse.

        Cherche un bloc JSON dans la reponse.
        """
        try:
            # Chercher un bloc JSON dans la reponse
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                if 'proposals' in data:
                    return data['proposals']

            # Essayer de parser directement si c'est du JSON
            if content.strip().startswith('{'):
                data = json.loads(content)
                if 'proposals' in data:
                    return data['proposals']

            return None

        except (json.JSONDecodeError, AttributeError):
            return None

    def _format_response_with_proposals(self, content: str, proposals: List[Dict]) -> str:
        """
        Formate la reponse en incluant les proposals de maniere lisible.
        """
        # Retirer le bloc JSON brut de la reponse
        content = re.sub(r'```json\s*.*?\s*```', '', content, flags=re.DOTALL)

        # Construire l'affichage des proposals
        proposals_text = "\n## Codes TARIC Proposes\n\n"

        for i, prop in enumerate(proposals, 1):
            code = prop.get('code_taric', 'N/A')
            desc = prop.get('description', '')
            prob = prop.get('probability', 0)

            # Barre de progression
            bar_filled = int(prob / 5)  # 20 caracteres max
            bar_empty = 20 - bar_filled
            bar = '█' * bar_filled + '░' * bar_empty

            proposals_text += f"**{i}. {code}** - {desc}\n"
            proposals_text += f"   Precision: {prob}% {bar}\n\n"

        # Ajouter le raisonnement si present
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                if 'raisonnement_global' in data:
                    proposals_text += f"\n### Raisonnement\n{data['raisonnement_global']}\n"
        except:
            pass

        return content.strip() + proposals_text

    def generate_classification_summary(self, proposal: Dict) -> str:
        """
        Genere un resume de la classification pour affichage final.

        Args:
            proposal: La proposition selectionnee

        Returns:
            Texte du resume
        """
        return TARIC_VALIDATION_MESSAGE.format(
            code_taric=proposal.get('code_taric', 'N/A'),
            code_nc=proposal.get('code_nc', 'N/A'),
            code_sh=proposal.get('code_sh', 'N/A'),
            probability=proposal.get('probability', 0),
            justification=proposal.get('justification', 'Non specifiee')
        )

    def generate_conversation_summary(self, messages: List[Dict], selected_proposal: Dict) -> Dict[str, Any]:
        """
        Genere un resume de la conversation et de la classification.

        Args:
            messages: Liste des messages de la conversation
            selected_proposal: La proposition selectionnee

        Returns:
            Dict avec le resume structure
        """
        # Compter les messages
        user_messages = [m for m in messages if m.get('role') == 'user']
        assistant_messages = [m for m in messages if m.get('role') == 'assistant']

        # Extraire les points cles
        key_points = []

        # Analyser les messages pour extraire les informations importantes
        for msg in messages:
            content = msg.get('content', '')
            if 'photo' in content.lower() or 'fiche' in content.lower():
                if 'telecharge' in content.lower() or 'ajoute' in content.lower():
                    key_points.append("Documents telecharges et analyses")
            if 'taric' in content.lower() and any(char.isdigit() for char in content):
                key_points.append("Codes TARIC proposes et evalues")

        # Construire le resume
        summary = {
            'classification': {
                'code_taric': selected_proposal.get('code_taric'),
                'code_nc': selected_proposal.get('code_nc'),
                'code_sh': selected_proposal.get('code_sh'),
                'description': selected_proposal.get('description'),
                'precision': selected_proposal.get('probability'),
                'justification': selected_proposal.get('justification'),
            },
            'conversation': {
                'total_messages': len(messages),
                'user_messages': len(user_messages),
                'assistant_messages': len(assistant_messages),
            },
            'key_points': list(set(key_points)) if key_points else ['Classification effectuee'],
            'documents_used': {
                'photos': list(self.expedition.documents.filter(type='photo').values_list('nom_original', flat=True)),
                'fiches_techniques': list(self.expedition.documents.filter(type='fiche_technique').values_list('nom_original', flat=True)),
            }
        }

        return summary
