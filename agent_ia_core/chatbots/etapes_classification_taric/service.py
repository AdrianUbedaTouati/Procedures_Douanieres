"""
Service pour le chatbot de classification TARIC.
Reutilise ChatAgentService avec des prompts et tools specialises.

Utilise la nouvelle structure:
- ExpeditionEtape (table intermediaire)
- ClassificationData (donnees specifiques 1:1)
- ExpeditionDocument (fichiers lies a l'etape)
"""
import json
import re
import sys
from typing import Dict, Any, List, Optional

from openai import OpenAI

from .config import CHATBOT_CONFIG
from .prompts import (
    TARIC_SYSTEM_PROMPT,
    TARIC_WELCOME_MESSAGE,
    TARIC_ANALYSIS_PROMPT,
    TARIC_VALIDATION_MESSAGE
)

# Schema JSON pour l'extraction structuree des codes TARIC
# IMPORTANT: En mode strict, TOUS les champs de properties doivent etre dans required
TARIC_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "proposals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code_taric": {"type": "string", "description": "Code TARIC 10 chiffres sans espaces"},
                    "description": {"type": "string", "description": "Description officielle du code"},
                    "probability": {"type": "integer", "description": "Probabilite estimee en %"},
                    "droits_douane": {"type": "string", "description": "Taux droits de douane (ex: 2.7%)"},
                    "tva": {"type": "string", "description": "Taux TVA (ex: 20%)"},
                    "justification": {"type": "string", "description": "Justification du choix"}
                },
                "required": ["code_taric", "description", "probability", "droits_douane", "tva", "justification"],
                "additionalProperties": False
            }
        }
    },
    "required": ["proposals"],
    "additionalProperties": False
}


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
        self._etape = None
        self._classification_data = None

    @property
    def etape(self):
        """Retourne l'etape de classification (etape 1)."""
        if self._etape is None:
            self._etape = self.expedition.get_etape(1)
        return self._etape

    @property
    def classification_data(self):
        """Retourne les donnees de classification."""
        if self._classification_data is None:
            self._classification_data = self.etape.get_data()
        return self._classification_data

    def _get_chat_service(self):
        """Obtenir le service de chat sous-jacent."""
        if self._chat_service is None:
            from apps.chat.services import ChatAgentService
            # Passer le contexte expedition pour les tools qui en ont besoin
            etape_id = self.etape.id if self.etape else None
            self._chat_service = ChatAgentService(
                self.user,
                expedition_id=self.expedition.id,
                etape_id=etape_id,
                system_prompt=TARIC_SYSTEM_PROMPT
            )
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
        Recupere les informations sur les documents de l'etape de classification.

        Returns:
            Dict avec photos et fiches_techniques
        """
        # Les documents sont maintenant lies a l'etape, pas a l'expedition
        photos = list(self.etape.documents.filter(type='photo').values(
            'id', 'nom_original', 'fichier', 'created_at'
        ))
        fiches = list(self.etape.documents.filter(type='fiche_technique').values(
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

            # S'assurer que metadata existe
            if 'metadata' not in result:
                result['metadata'] = {}

            # Analyser la reponse pour extraire les proposals
            proposals = self._extract_proposals(result['content'])
            print(f"[TARIC_SERVICE] Proposals extracted: {proposals is not None and len(proposals) if proposals else 0}", file=sys.stderr)

            # Ajouter les proposals au metadata
            result['metadata']['proposals'] = proposals
            result['metadata']['has_proposals'] = proposals is not None and len(proposals) > 0
            print(f"[TARIC_SERVICE] Result metadata has_proposals: {result['metadata']['has_proposals']}", file=sys.stderr)

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

        # Ajouter info sur classification existante si presente
        if self.classification_data and self.classification_data.code_taric:
            context_parts.append(f"Classification actuelle: {self.classification_data.formatted_code}")

        return '\n'.join(context_parts)

    def _extract_proposals(self, content: str) -> Optional[List[Dict]]:
        """
        Extrait les propositions de codes TARIC de la reponse.

        Utilise TOUJOURS OpenAI avec JSON structured output pour garantir un format valide.
        Simple, robuste et economique (gpt-4o-mini).
        """
        print(f"[TARIC_SERVICE] Extracting proposals with OpenAI structured output ({len(content)} chars)", file=sys.stderr)
        return self._extract_with_openai(content)

    def _extract_with_openai(self, content: str) -> Optional[List[Dict]]:
        """
        Utilise OpenAI avec response_format pour extraire les codes TARIC.
        Garantit un JSON valide grace au mode structured output.
        """
        try:
            # Utiliser directement la llm_api_key de l'utilisateur (OpenAI)
            api_key = getattr(self.user, 'llm_api_key', None)

            if not api_key:
                print(f"[TARIC_SERVICE] No API key found for user", file=sys.stderr)
                return None

            print(f"[TARIC_SERVICE] Calling OpenAI gpt-4o-mini for extraction", file=sys.stderr)
            client = OpenAI(api_key=api_key)

            extraction_prompt = """Analyse le texte suivant et extrait TOUS les codes TARIC mentionnes.

Pour chaque code TARIC trouve, extrais:
- code_taric: le code a EXACTEMENT 10 chiffres (SANS espaces, points ou tirets)
- description: la description officielle du code
- probability: la probabilite/precision estimee (nombre entier de 0 a 100)
- droits_douane: le taux de droits de douane (ex: "2.7%", "0%")
- tva: le taux de TVA (ex: "20%")
- justification: la raison du choix de ce code

REGLES CRITIQUES:
- Les codes TARIC font EXACTEMENT 10 chiffres, pas plus, pas moins
- Nettoie les codes: "7013 99 00 00" devient "7013990000"
- Si le code a 8 chiffres (NC), ajoute "00" a la fin: "70139900" devient "7013990000"
- Si le code a 6 chiffres (SH), ajoute "0000" a la fin: "701399" devient "7013990000"
- REJETTE les codes avec X ou similaires: "7013XXXXXX" n'est PAS valide
- Si le code contient des X, essaie de deviner les chiffres manquants ou ignore-le
- Si une info manque (droits, tva), mets une valeur par defaut ("0%" ou "20%")

TEXTE A ANALYSER:
"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Tu extrais des codes TARIC depuis du texte. Reponds uniquement en JSON."},
                    {"role": "user", "content": extraction_prompt + content}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "taric_proposals",
                        "strict": True,
                        "schema": TARIC_EXTRACTION_SCHEMA
                    }
                },
                temperature=0.1,
                max_tokens=2000
            )

            result_text = response.choices[0].message.content
            print(f"[TARIC_SERVICE] OpenAI extraction response: {result_text[:200]}...", file=sys.stderr)

            data = json.loads(result_text)
            if 'proposals' in data and len(data['proposals']) > 0:
                proposals = self._ensure_proposal_fields(data['proposals'])
                print(f"[TARIC_SERVICE] OpenAI extracted {len(proposals)} proposals", file=sys.stderr)
                return proposals

            print(f"[TARIC_SERVICE] OpenAI returned no proposals", file=sys.stderr)
            return None

        except Exception as e:
            print(f"[TARIC_SERVICE] OpenAI extraction error: {e}", file=sys.stderr)
            return None

    def _ensure_proposal_fields(self, proposals: List[Dict]) -> List[Dict]:
        """
        S'assure que tous les champs obligatoires sont presents dans les proposals.
        Filtre les codes invalides (avec X ou incomplets).
        """
        valid_proposals = []

        for prop in proposals:
            code_taric = prop.get('code_taric', '')

            # Nettoyer le code: enlever espaces, points, tirets
            code_taric = re.sub(r'[\s.\-]', '', code_taric)

            # Rejeter les codes avec X ou non numeriques
            if 'X' in code_taric.upper() or not code_taric.isdigit():
                print(f"[TARIC_SERVICE] Rejecting invalid code: {prop.get('code_taric')}", file=sys.stderr)
                continue

            # Completer les codes trop courts
            if len(code_taric) == 8:
                code_taric = code_taric + '00'
            elif len(code_taric) == 6:
                code_taric = code_taric + '0000'
            elif len(code_taric) != 10:
                print(f"[TARIC_SERVICE] Rejecting code with wrong length ({len(code_taric)}): {code_taric}", file=sys.stderr)
                continue

            prop['code_taric'] = code_taric

            # Codes derives
            if not prop.get('code_nc'):
                prop['code_nc'] = code_taric[:8]
            if not prop.get('code_sh'):
                prop['code_sh'] = code_taric[:6]

            # Taxes avec valeurs par defaut
            if not prop.get('droits_douane'):
                prop['droits_douane'] = '-'
            if not prop.get('tva'):
                prop['tva'] = '20%'

            # Lien tarifdouanier.eu
            if not prop.get('lien_taric'):
                prop['lien_taric'] = f"https://www.tarifdouanier.eu/2026/{code_taric[:8]}"

            valid_proposals.append(prop)

        print(f"[TARIC_SERVICE] Valid proposals after filtering: {len(valid_proposals)}", file=sys.stderr)
        return valid_proposals

    def _format_response_with_proposals(self, content: str, proposals: List[Dict]) -> str:
        """
        Formate la reponse en gardant le texte explicatif du LLM et retirant seulement le JSON brut.
        Les boutons de propositions sont affiches separement par le frontend.

        Le LLM genere maintenant:
        1. Une analyse textuelle detaillee (PARTIE 1)
        2. Un bloc JSON structure (PARTIE 2)

        On garde la PARTIE 1 et on retire le JSON (PARTIE 2) car les boutons l'affichent.
        """
        # Retirer le bloc JSON brut de la reponse (pas visible pour l'utilisateur)
        # Le frontend affiche les boutons a partir des proposals extraites
        content = re.sub(r'```json\s*.*?\s*```', '', content, flags=re.DOTALL)

        # Nettoyer les lignes vides multiples
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Ajouter indication pour les boutons
        content = content.strip()
        content += "\n\n---\n*Cliquez sur un bouton ci-dessous pour sélectionner votre code TARIC.*"

        return content

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

        # Construire le resume (utilisant la nouvelle structure)
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
                'photos': list(self.etape.documents.filter(type='photo').values_list('nom_original', flat=True)),
                'fiches_techniques': list(self.etape.documents.filter(type='fiche_technique').values_list('nom_original', flat=True)),
            }
        }

        return summary
