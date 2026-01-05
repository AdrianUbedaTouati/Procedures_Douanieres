"""
Tests pour l'etape de classification et le chat IA.
- Chat de classification
- Propositions TARIC
- Validation de la classification
- Service de classification
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json

from apps.expeditions.models import (
    Expedition, ExpeditionEtape, ClassificationData
)

User = get_user_model()


class ClassificationViewTestCase(TestCase):
    """Tests pour les vues de classification."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser@example.com', password='testpass123')

        self.expedition = Expedition.objects.create(
            user=self.user,
            nom_article='Ordinateur portable Dell XPS',
            description='Laptop professionnel 15 pouces',
            direction='FR_DZ'
        )

    def test_classification_page_loads(self):
        """Page de classification accessible."""
        url = reverse(
            'apps_expeditions:classification',
            kwargs={'pk': self.expedition.pk}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.expedition.reference)

    def test_classification_context_has_expedition(self):
        """Le contexte contient l'expedition."""
        url = reverse(
            'apps_expeditions:classification',
            kwargs={'pk': self.expedition.pk}
        )
        response = self.client.get(url)

        self.assertIn('expedition', response.context)
        self.assertEqual(
            response.context['expedition'].id,
            self.expedition.id
        )

    def test_classification_context_has_etape(self):
        """Le contexte contient l'etape."""
        url = reverse(
            'apps_expeditions:classification',
            kwargs={'pk': self.expedition.pk}
        )
        response = self.client.get(url)

        self.assertIn('etape', response.context)
        self.assertEqual(response.context['etape'].numero, 1)

    def test_classification_requires_login(self):
        """Page classification necessite authentification."""
        self.client.logout()
        url = reverse(
            'apps_expeditions:classification',
            kwargs={'pk': self.expedition.pk}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


class ClassificationChatTestCase(TestCase):
    """Tests pour le chat de classification."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        self.expedition = Expedition.objects.create(
            user=self.user,
            nom_article='Test Product',
            direction='FR_DZ'
        )
        self.etape = self.expedition.get_etape(1)
        self.classification_data = self.etape.get_data()

    def test_add_user_message(self):
        """Ajouter un message utilisateur."""
        self.classification_data.add_message(
            role='user',
            content='Mon produit est un ordinateur portable'
        )

        self.assertEqual(len(self.classification_data.chat_historique), 1)
        msg = self.classification_data.chat_historique[0]
        self.assertEqual(msg['role'], 'user')
        self.assertEqual(msg['content'], 'Mon produit est un ordinateur portable')

    def test_add_assistant_message(self):
        """Ajouter un message assistant."""
        self.classification_data.add_message(
            role='assistant',
            content='Je vais analyser votre produit'
        )

        msg = self.classification_data.chat_historique[0]
        self.assertEqual(msg['role'], 'assistant')

    def test_message_has_timestamp(self):
        """Message a un timestamp."""
        self.classification_data.add_message(
            role='user',
            content='Test'
        )

        msg = self.classification_data.chat_historique[0]
        self.assertIn('timestamp', msg)

    def test_multiple_messages_in_order(self):
        """Messages gardes dans l'ordre."""
        self.classification_data.add_message(role='user', content='Message 1')
        self.classification_data.add_message(role='assistant', content='Message 2')
        self.classification_data.add_message(role='user', content='Message 3')

        self.assertEqual(len(self.classification_data.chat_historique), 3)
        self.assertEqual(
            self.classification_data.chat_historique[0]['content'],
            'Message 1'
        )
        self.assertEqual(
            self.classification_data.chat_historique[2]['content'],
            'Message 3'
        )

    def test_chat_persisted_to_database(self):
        """Chat persiste en base de donnees."""
        self.classification_data.add_message(
            role='user',
            content='Test persistence'
        )
        self.classification_data.save()

        # Recharger depuis la BDD
        fresh_data = ClassificationData.objects.get(id=self.classification_data.id)
        self.assertEqual(len(fresh_data.chat_historique), 1)
        self.assertEqual(
            fresh_data.chat_historique[0]['content'],
            'Test persistence'
        )


class TARICPropositionsTestCase(TestCase):
    """Tests pour les propositions TARIC."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        self.expedition = Expedition.objects.create(
            user=self.user,
            nom_article='Test',
            direction='FR_DZ'
        )
        self.etape = self.expedition.get_etape(1)
        self.classification_data = self.etape.get_data()

    def test_set_propositions(self):
        """Definir les propositions."""
        propositions = [
            {
                'code_taric': '8471300000',
                'code_nc': '84713000',
                'code_sh': '847130',
                'probability': 85,
                'description': 'Machines automatiques de traitement',
                'justification': 'Ordinateur portable'
            },
            {
                'code_taric': '8471410000',
                'code_nc': '84714100',
                'code_sh': '847141',
                'probability': 70,
                'description': 'Autres machines automatiques',
                'justification': 'Alternative'
            }
        ]

        self.classification_data.set_propositions(propositions)

        self.assertEqual(len(self.classification_data.propositions), 2)

    def test_propositions_kept_in_order(self):
        """Propositions gardees dans l'ordre fourni."""
        propositions = [
            {'code_taric': '1111111111', 'probability': 50},
            {'code_taric': '2222222222', 'probability': 90},
            {'code_taric': '3333333333', 'probability': 70}
        ]

        self.classification_data.set_propositions(propositions)

        # Les propositions sont gardees dans l'ordre fourni
        self.assertEqual(
            self.classification_data.propositions[0]['probability'],
            50
        )

    def test_select_proposition(self):
        """Selectionner une proposition."""
        propositions = [
            {'code_taric': '8471300000', 'probability': 85},
            {'code_taric': '8471410000', 'probability': 70}
        ]
        self.classification_data.set_propositions(propositions)
        self.classification_data.select_proposition(1)

        self.assertEqual(self.classification_data.proposition_selectionnee, 1)

    def test_selected_proposal_property(self):
        """Propriete selected_proposal."""
        propositions = [
            {'code_taric': '8471300000', 'probability': 85},
            {'code_taric': '8471410000', 'probability': 70}
        ]
        self.classification_data.set_propositions(propositions)
        self.classification_data.select_proposition(0)

        selected = self.classification_data.selected_proposal
        self.assertEqual(selected['code_taric'], '8471300000')

    def test_no_selection_returns_none(self):
        """Pas de selection retourne None."""
        self.assertIsNone(self.classification_data.selected_proposal)

    def test_propositions_persisted(self):
        """Propositions persistees en BDD."""
        propositions = [
            {'code_taric': '8471300000', 'probability': 85}
        ]
        self.classification_data.set_propositions(propositions)
        self.classification_data.save()

        fresh_data = ClassificationData.objects.get(id=self.classification_data.id)
        self.assertEqual(len(fresh_data.propositions), 1)


class ClassificationValidationTestCase(TestCase):
    """Tests pour la validation de la classification."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        self.expedition = Expedition.objects.create(
            user=self.user,
            nom_article='Test',
            direction='FR_DZ'
        )
        self.etape = self.expedition.get_etape(1)
        self.classification_data = self.etape.get_data()

    def test_validate_classification_sets_codes(self):
        """Valider classification definit les codes."""
        propositions = [
            {
                'code_taric': '8471300000',
                'code_nc': '84713000',
                'code_sh': '847130',
                'probability': 85
            }
        ]
        self.classification_data.set_propositions(propositions)
        self.classification_data.select_proposition(0)
        self.classification_data.validate_classification()

        self.assertEqual(self.classification_data.code_sh, '847130')
        self.assertEqual(self.classification_data.code_nc, '84713000')
        self.assertEqual(self.classification_data.code_taric, '8471300000')

    def test_validate_without_selection_returns_false(self):
        """Valider sans selection retourne False."""
        propositions = [{'code_taric': '8471300000', 'probability': 85}]
        self.classification_data.set_propositions(propositions)

        result = self.classification_data.validate_classification()
        self.assertFalse(result)

    def test_formatted_code_property(self):
        """Code formate correctement."""
        self.classification_data.code_taric = '8471300000'
        self.classification_data.save()

        formatted = self.classification_data.formatted_code
        self.assertEqual(formatted, '8471.30.00.00')

    def test_formatted_code_empty_when_no_code(self):
        """Code formate vide si pas de code."""
        self.assertEqual(self.classification_data.formatted_code, "")


class ClassificationEtapeProgressTestCase(TestCase):
    """Tests pour la progression de l'etape de classification."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        self.expedition = Expedition.objects.create(
            user=self.user,
            nom_article='Test',
            direction='FR_DZ'
        )

    def test_etape_1_initial_status_en_cours(self):
        """Etape 1 commence en_cours."""
        etape = self.expedition.get_etape(1)
        self.assertEqual(etape.statut, 'en_cours')

    def test_etape_2_initial_status_en_attente(self):
        """Etape 2 commence en_attente."""
        etape = self.expedition.get_etape(2)
        self.assertEqual(etape.statut, 'en_attente')

    def test_marquer_termine_advances_to_etape_2(self):
        """Terminer etape 1 active etape 2."""
        etape1 = self.expedition.get_etape(1)
        etape2 = self.expedition.get_etape(2)

        etape1.marquer_termine()
        etape2.refresh_from_db()

        self.assertEqual(etape1.statut, 'termine')
        self.assertEqual(etape2.statut, 'en_cours')

    def test_completed_at_set_on_termine(self):
        """completed_at defini quand termine."""
        etape = self.expedition.get_etape(1)
        self.assertIsNone(etape.completed_at)

        etape.marquer_termine()

        self.assertIsNotNone(etape.completed_at)


class ClassificationDataRelationsTestCase(TestCase):
    """Tests pour les relations ClassificationData."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        self.expedition = Expedition.objects.create(
            user=self.user,
            nom_article='Test',
            direction='FR_DZ'
        )

    def test_classification_data_created_automatically(self):
        """ClassificationData cree automatiquement."""
        etape = self.expedition.get_etape(1)
        data = etape.get_data()

        self.assertIsInstance(data, ClassificationData)

    def test_one_classification_data_per_etape(self):
        """Un seul ClassificationData par etape."""
        etape = self.expedition.get_etape(1)

        self.assertEqual(
            ClassificationData.objects.filter(etape=etape).count(),
            1
        )

    def test_classification_data_cascade_delete(self):
        """ClassificationData supprime avec expedition."""
        self.assertEqual(ClassificationData.objects.count(), 1)

        self.expedition.delete()

        self.assertEqual(ClassificationData.objects.count(), 0)


# Note: ClassificationChatAPITestCase supprime car les endpoints API
# ne sont pas encore implementes comme routes separees.
# Le chat de classification est integre dans la vue principale.

