"""
Tests pour le module Expeditions.
- Creation d'expedition
- Liste des expeditions
- Detail d'une expedition
- Suppression d'expedition
- Gestion des etapes
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.expeditions.models import (
    Expedition, ExpeditionEtape, ExpeditionDocument,
    ClassificationData, DocumentsData, TransmissionData,
    PaiementData, OEAData
)

User = get_user_model()


class ExpeditionCreationTestCase(TestCase):
    """Tests pour la creation d'expeditions."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser@example.com', password='testpass123')
        self.create_url = reverse('apps_expeditions:create')

    def test_create_expedition_page_accessible(self):
        """La page de creation est accessible."""
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

    def test_create_expedition_with_valid_data(self):
        """Creer une expedition avec donnees valides."""
        response = self.client.post(self.create_url, {
            'nom_article': 'Ordinateur portable Dell XPS 15',
            'description': 'Laptop pour usage professionnel',
            'direction': 'FR_DZ'
        })

        # Verifier la redirection apres creation
        self.assertEqual(response.status_code, 302)

        # Verifier que l'expedition existe
        expedition = Expedition.objects.filter(
            nom_article='Ordinateur portable Dell XPS 15'
        ).first()
        self.assertIsNotNone(expedition)
        self.assertEqual(expedition.user, self.user)
        self.assertEqual(expedition.direction, 'FR_DZ')
        self.assertEqual(expedition.statut, 'en_cours')

    def test_expedition_creates_5_etapes(self):
        """Une nouvelle expedition cree 5 etapes."""
        self.client.post(self.create_url, {
            'nom_article': 'Test Product',
            'direction': 'FR_DZ'
        })

        expedition = Expedition.objects.first()
        self.assertEqual(expedition.etapes.count(), 5)

    def test_expedition_etapes_have_correct_types(self):
        """Les etapes ont les bons types."""
        self.client.post(self.create_url, {
            'nom_article': 'Test Product',
            'direction': 'FR_DZ'
        })

        expedition = Expedition.objects.first()
        etapes = expedition.etapes.all().order_by('numero')

        expected_types = ['classification', 'documents', 'transmission', 'paiement', 'oea']
        for etape, expected_type in zip(etapes, expected_types):
            self.assertEqual(etape.type_etape, expected_type)

    def test_expedition_etapes_have_data_tables(self):
        """Chaque etape a sa table de donnees associee."""
        self.client.post(self.create_url, {
            'nom_article': 'Test Product',
            'direction': 'FR_DZ'
        })

        expedition = Expedition.objects.first()

        # Etape 1: ClassificationData
        etape1 = expedition.get_etape(1)
        self.assertIsNotNone(etape1.get_data())
        self.assertIsInstance(etape1.get_data(), ClassificationData)

        # Etape 2: DocumentsData
        etape2 = expedition.get_etape(2)
        self.assertIsNotNone(etape2.get_data())
        self.assertIsInstance(etape2.get_data(), DocumentsData)

        # Etape 3: TransmissionData
        etape3 = expedition.get_etape(3)
        self.assertIsNotNone(etape3.get_data())
        self.assertIsInstance(etape3.get_data(), TransmissionData)

        # Etape 4: PaiementData
        etape4 = expedition.get_etape(4)
        self.assertIsNotNone(etape4.get_data())
        self.assertIsInstance(etape4.get_data(), PaiementData)

        # Etape 5: OEAData
        etape5 = expedition.get_etape(5)
        self.assertIsNotNone(etape5.get_data())
        self.assertIsInstance(etape5.get_data(), OEAData)

    def test_expedition_reference_generated(self):
        """La reference est generee automatiquement."""
        self.client.post(self.create_url, {
            'nom_article': 'Test Product',
            'direction': 'FR_DZ'
        })

        expedition = Expedition.objects.first()
        self.assertTrue(expedition.reference.startswith('EXP-'))

    def test_create_expedition_without_nom_article_fails(self):
        """Creer sans nom_article echoue."""
        response = self.client.post(self.create_url, {
            'direction': 'FR_DZ'
        })
        self.assertEqual(response.status_code, 200)  # Reste sur le formulaire
        self.assertEqual(Expedition.objects.count(), 0)


class ExpeditionListTestCase(TestCase):
    """Tests pour la liste des expeditions."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser@example.com', password='testpass123')
        self.list_url = reverse('apps_expeditions:list')

    def test_list_shows_only_user_expeditions(self):
        """La liste montre uniquement les expeditions de l'utilisateur."""
        # Creer expeditions pour l'utilisateur
        Expedition.objects.create(
            user=self.user,
            nom_article='My Product',
            direction='FR_DZ'
        )
        # Creer expedition pour autre utilisateur
        Expedition.objects.create(
            user=self.other_user,
            nom_article='Other Product',
            direction='DZ_FR'
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

        expeditions = response.context['expeditions']
        self.assertEqual(expeditions.count(), 1)
        self.assertEqual(expeditions.first().nom_article, 'My Product')

    def test_list_shows_statistics(self):
        """La liste affiche les statistiques."""
        # Creer expeditions avec differents statuts
        Expedition.objects.create(
            user=self.user,
            nom_article='En cours',
            direction='FR_DZ',
            statut='en_cours'
        )
        Expedition.objects.create(
            user=self.user,
            nom_article='Terminee',
            direction='FR_DZ',
            statut='termine'
        )

        response = self.client.get(self.list_url)
        stats = response.context['stats']

        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['en_cours'], 1)
        self.assertEqual(stats['terminees'], 1)


class ExpeditionDetailTestCase(TestCase):
    """Tests pour le detail d'une expedition."""

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
            nom_article='Test Product',
            description='Description du produit',
            direction='FR_DZ'
        )

    def test_detail_page_accessible(self):
        """La page de detail est accessible."""
        url = reverse('apps_expeditions:detail', kwargs={'pk': self.expedition.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_detail_shows_all_etapes(self):
        """Le detail affiche toutes les etapes."""
        url = reverse('apps_expeditions:detail', kwargs={'pk': self.expedition.pk})
        response = self.client.get(url)

        etapes = response.context['etapes']
        self.assertEqual(etapes.count(), 5)

    def test_detail_shows_expedition_info(self):
        """Le detail affiche les informations de l'expedition."""
        url = reverse('apps_expeditions:detail', kwargs={'pk': self.expedition.pk})
        response = self.client.get(url)

        self.assertContains(response, 'Test Product')
        self.assertContains(response, self.expedition.reference)

    def test_cannot_access_other_user_expedition(self):
        """On ne peut pas acceder a l'expedition d'un autre utilisateur."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        other_expedition = Expedition.objects.create(
            user=other_user,
            nom_article='Other Product',
            direction='FR_DZ'
        )

        url = reverse('apps_expeditions:detail', kwargs={'pk': other_expedition.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class ExpeditionDeleteTestCase(TestCase):
    """Tests pour la suppression d'expeditions."""

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
            nom_article='Test Product',
            direction='FR_DZ'
        )

    def test_delete_expedition(self):
        """Supprimer une expedition."""
        url = reverse('apps_expeditions:delete', kwargs={'pk': self.expedition.pk})
        response = self.client.post(url)

        # Devrait rediriger vers la liste
        self.assertEqual(response.status_code, 302)

        # L'expedition ne devrait plus exister
        self.assertFalse(Expedition.objects.filter(pk=self.expedition.pk).exists())

    def test_delete_cascade_etapes(self):
        """Supprimer cascade les etapes."""
        etape_count_before = ExpeditionEtape.objects.count()

        url = reverse('apps_expeditions:delete', kwargs={'pk': self.expedition.pk})
        self.client.post(url)

        # Les etapes devraient etre supprimees
        self.assertEqual(ExpeditionEtape.objects.count(), etape_count_before - 5)

    def test_cannot_delete_other_user_expedition(self):
        """On ne peut pas supprimer l'expedition d'un autre utilisateur."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        other_expedition = Expedition.objects.create(
            user=other_user,
            nom_article='Other Product',
            direction='FR_DZ'
        )

        url = reverse('apps_expeditions:delete', kwargs={'pk': other_expedition.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

        # L'expedition devrait toujours exister
        self.assertTrue(Expedition.objects.filter(pk=other_expedition.pk).exists())


class ExpeditionProgressTestCase(TestCase):
    """Tests pour la progression des expeditions."""

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

    def test_initial_progress_is_zero(self):
        """La progression initiale est 0%."""
        self.assertEqual(self.expedition.get_progress_percentage(), 0)

    def test_progress_updates_with_completed_etapes(self):
        """La progression augmente avec les etapes terminees."""
        etape1 = self.expedition.get_etape(1)
        etape1.marquer_termine()

        self.assertEqual(self.expedition.get_progress_percentage(), 20)

    def test_etape_courante_updates(self):
        """L'etape courante se met a jour."""
        self.assertEqual(self.expedition.etape_courante, 1)

        etape1 = self.expedition.get_etape(1)
        etape1.marquer_termine()

        self.expedition.refresh_from_db()
        self.assertEqual(self.expedition.etape_courante, 2)
