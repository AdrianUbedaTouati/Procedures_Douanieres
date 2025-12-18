"""
Service de classification douanière.
Intègre l'agent IA pour analyser les documents et retourner les codes SH/NC/TARIC.
"""

import logging
import re
from typing import Tuple

from django.conf import settings

logger = logging.getLogger(__name__)


class ClassificationService:
    """
    Service pour classifier un produit via l'IA.

    Analyse une photo ou un document PDF et retourne les codes douaniers
    (SH, NC, TARIC) avec leur niveau de confiance.
    """

    def __init__(self, user, expedition):
        """
        Initialise le service de classification.

        Args:
            user: L'utilisateur Django
            expedition: L'objet Expedition
        """
        self.user = user
        self.expedition = expedition
        self.agent = None

    def _init_agent(self):
        """Initialise l'agent IA si nécessaire."""
        if self.agent is None:
            try:
                from agent_ia_core import FunctionCallingAgent
                from apps.core.models import UserProfile

                # Récupérer les préférences LLM de l'utilisateur
                profile = UserProfile.objects.filter(user=self.user).first()

                llm_provider = 'ollama'  # Par défaut
                model_name = 'llama3.2'

                if profile:
                    llm_provider = profile.default_llm_provider or 'ollama'
                    model_name = profile.default_model_name or 'llama3.2'

                self.agent = FunctionCallingAgent(
                    llm_provider=llm_provider,
                    model_name=model_name
                )

            except Exception as e:
                logger.error(f"Erreur initialisation agent: {e}")
                raise

    def analyser_document(self, document) -> dict:
        """
        Analyse un document (photo ou PDF) et retourne les codes douaniers.

        Args:
            document: L'objet ExpeditionDocument à analyser

        Returns:
            dict: {
                'code_sh': '8471.30',
                'code_nc': '8471.30.00',
                'code_taric': '8471.30.00.00',
                'confiance_sh': 0.95,
                'confiance_nc': 0.88,
                'confiance_taric': 0.82,
                'justification': '...',
                'description_produit': '...',
            }
        """
        self._init_agent()

        # 1. Extraire le contenu du document
        if document.is_image:
            contenu = self._analyser_photo(document)
        elif document.is_pdf:
            contenu = self._extraire_texte_pdf(document)
        else:
            raise ValueError(f"Type de document non supporté: {document.extension}")

        # 2. Construire le prompt de classification
        prompt = self._build_classification_prompt(contenu)

        # 3. Appeler l'agent IA
        try:
            response = self.agent.query(prompt)
            result = self._parser_resultat(response)
        except Exception as e:
            logger.error(f"Erreur classification IA: {e}")
            # Retourner un résultat vide en cas d'erreur
            result = {
                'code_sh': '',
                'code_nc': '',
                'code_taric': '',
                'confiance_sh': 0,
                'confiance_nc': 0,
                'confiance_taric': 0,
                'justification': f"Erreur lors de la classification: {e}",
                'erreur': True,
            }

        return result

    def _analyser_photo(self, document) -> str:
        """
        Analyse une photo du produit.

        Pour l'instant, retourne une description basique.
        À améliorer avec un modèle de vision (GPT-4V, Claude Vision, etc.)
        """
        description = f"""
        Photo du produit: {document.nom_original}
        Nom de l'article: {self.expedition.nom_article}
        Description fournie: {self.expedition.description or 'Non fournie'}
        Direction: {self.expedition.get_direction_display()}
        """

        return description.strip()

    def _extraire_texte_pdf(self, document) -> str:
        """
        Extrait le texte d'un document PDF (fiche technique).
        """
        try:
            import PyPDF2

            fichier_path = document.fichier.path

            with open(fichier_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages[:5]:  # Max 5 pages
                    text += page.extract_text() + "\n"

            text = f"""
            Nom de l'article: {self.expedition.nom_article}
            Description: {self.expedition.description or 'Non fournie'}

            --- Contenu de la fiche technique ---
            {text[:5000]}
            """

            return text.strip()

        except ImportError:
            logger.warning("PyPDF2 non installé, utilisation de la description seule")
            return f"""
            Nom de l'article: {self.expedition.nom_article}
            Description: {self.expedition.description or 'Non fournie'}
            Document: {document.nom_original}
            """
        except Exception as e:
            logger.error(f"Erreur extraction PDF: {e}")
            return f"""
            Nom de l'article: {self.expedition.nom_article}
            Description: {self.expedition.description or 'Non fournie'}
            Erreur lecture PDF: {e}
            """

    def _build_classification_prompt(self, contenu: str) -> str:
        """Construit le prompt de classification."""
        from agent_ia_core.chatbots.etapes_classification_taric.prompts import create_classification_prompt

        product_info = {
            'description': contenu,
            'direction': self.expedition.get_direction_display(),
        }

        return create_classification_prompt(product_info)

    def _parser_resultat(self, response: str) -> dict:
        """
        Parse la réponse de l'agent IA pour extraire les codes.
        """
        result = {
            'code_sh': '',
            'code_nc': '',
            'code_taric': '',
            'confiance_sh': 0.0,
            'confiance_nc': 0.0,
            'confiance_taric': 0.0,
            'justification': response,
            'description_produit': '',
        }

        # Extraire le code SH (format: XXXX.XX ou XXXXXX)
        sh_match = re.search(r'(?:SH|HS)[:\s]*(\d{4}\.?\d{2})', response, re.IGNORECASE)
        if sh_match:
            result['code_sh'] = sh_match.group(1)
            result['confiance_sh'] = 0.85

        # Extraire le code NC (format: XXXX.XX.XX ou XXXXXXXX)
        nc_match = re.search(r'(?:NC)[:\s]*(\d{4}\.?\d{2}\.?\d{2})', response, re.IGNORECASE)
        if nc_match:
            result['code_nc'] = nc_match.group(1)
            result['confiance_nc'] = 0.75

        # Extraire le code TARIC (format: XXXX.XX.XX.XX ou XXXXXXXXXX)
        taric_match = re.search(r'(?:TARIC)[:\s]*(\d{4}\.?\d{2}\.?\d{2}\.?\d{2})', response, re.IGNORECASE)
        if taric_match:
            result['code_taric'] = taric_match.group(1)
            result['confiance_taric'] = 0.65

        # Si pas de code NC mais code SH, estimer le NC
        if result['code_sh'] and not result['code_nc']:
            sh_clean = result['code_sh'].replace('.', '')
            if len(sh_clean) == 6:
                result['code_nc'] = f"{sh_clean[:4]}.{sh_clean[4:6]}.00"
                result['confiance_nc'] = 0.50

        # Si pas de code TARIC mais code NC, estimer le TARIC
        if result['code_nc'] and not result['code_taric']:
            nc_clean = result['code_nc'].replace('.', '')
            if len(nc_clean) >= 8:
                result['code_taric'] = f"{nc_clean[:4]}.{nc_clean[4:6]}.{nc_clean[6:8]}.00"
                result['confiance_taric'] = 0.40

        # Extraire la confiance si mentionnée explicitement
        conf_match = re.search(r'confiance[:\s]*(\d{1,3})\s*%', response, re.IGNORECASE)
        if conf_match:
            conf = int(conf_match.group(1)) / 100
            if result['code_sh']:
                result['confiance_sh'] = max(result['confiance_sh'], conf)

        return result


class ClassificationValidator:
    """
    Validateur de codes douaniers.
    Vérifie la cohérence et la validité des codes SH/NC/TARIC.
    """

    @staticmethod
    def valider_code_sh(code: str) -> Tuple[bool, str]:
        """
        Valide un code SH (6 chiffres).

        Returns:
            tuple: (is_valid, message)
        """
        code_clean = code.replace('.', '').replace(' ', '')

        if not code_clean:
            return False, "Le code SH est obligatoire"

        if not re.match(r'^\d{6}$', code_clean):
            return False, "Le code SH doit contenir exactement 6 chiffres"

        formatted = f"{code_clean[:4]}.{code_clean[4:6]}"

        return True, formatted

    @staticmethod
    def valider_code_nc(code: str) -> Tuple[bool, str]:
        """
        Valide un code NC (8 chiffres).

        Returns:
            tuple: (is_valid, message)
        """
        if not code:
            return True, ""

        code_clean = code.replace('.', '').replace(' ', '')

        if not re.match(r'^\d{8}$', code_clean):
            return False, "Le code NC doit contenir exactement 8 chiffres"

        formatted = f"{code_clean[:4]}.{code_clean[4:6]}.{code_clean[6:8]}"

        return True, formatted

    @staticmethod
    def valider_code_taric(code: str) -> Tuple[bool, str]:
        """
        Valide un code TARIC (10 chiffres).

        Returns:
            tuple: (is_valid, message)
        """
        if not code:
            return True, ""

        code_clean = code.replace('.', '').replace(' ', '')

        if not re.match(r'^\d{10}$', code_clean):
            return False, "Le code TARIC doit contenir exactement 10 chiffres"

        formatted = f"{code_clean[:4]}.{code_clean[4:6]}.{code_clean[6:8]}.{code_clean[8:10]}"

        return True, formatted
