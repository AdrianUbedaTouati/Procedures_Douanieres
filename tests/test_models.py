"""
Tests pour les modeles de donnees.
- Relations entre modeles
- Validations
- Methodes utilitaires
- Sauvegarde en base de donnees
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.expeditions.models import (
    Expedition, ExpeditionEtape, ExpeditionDocument,
    ClassificationData, DocumentsData, TransmissionData,
    PaiementData, OEAData
)

User = get_user_model()


class ExpeditionModelTestCase(TestCase):
    """Tests pour le modele Expedition."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )

    def test_create_expedition(self):
        """Creer une expedition."""
        expedition = Expedition.objects.create(
            user=self.user,
            nom_article='Laptop Dell XPS',
            description='Ordinateur portable professionnel',
            direction='FR_DZ'
        )

        self.assertIsNotNone(expedition.id)
        self.assertEqual(expedition.nom_article, 'Laptop Dell XPS')
        self.assertEqual(expedition.direction, 'FR_DZ')
        self.assertEqual(expedition.statut, 'brouillon')
        self.assertEqual(expedition.etape_courante, 1)

    def test_reference_auto_generated(self):
        """La reference est generee automatiquement."""
        expedition = Expedition.objects.create(
            user=self.user,
            nom_article='Test',
            direction='FR_DZ'
        )

        self.assertTrue(expedition.reference.startswith('EXP-'))
        self.assertIn('2025', expedition.reference)

    def test_reference_is_unique(self):
        """Les references sont uniques."""
        exp1 = Expedition.objects.create(
            user=self.user,
            nom_article='Test 1',
            direction='FR_DZ'
        )

        exp2 = Expedition.objects.create(
            user=self.user,
            nom_article='Test 2',
            direction='FR_DZ'
        )

        self.assertNotEqual(exp1.reference, exp2.reference)

    def test_etapes_created_on_save(self):
        """5 etapes creees automatiquement."""
        expedition = Expedition.objects.create(
            user=self.user,
            nom_article='Test',
            direction='FR_DZ'
        )

        self.assertEqual(expedition.etapes.count(), 5)

    def test_get_etape_by_number(self):
        """Recuperer une etape par son numero."""
        expedition = Expedition.objects.create(
            user=self.user,
            nom_article='Test',
            direction='FR_DZ'
        )

        etape = expedition.get_etape(1)
        self.assertIsNotNone(etape)
        self.assertEqual(etape.numero, 1)

    def test_get_direction_display(self):
        """Affichage de la direction."""
        expedition = Expedition.objects.create(
            user=self.user,
            nom_article='Test',
            direction='FR_DZ'
        )

        self.assertIn('France', expedition.get_direction_display())

    def test_progress_percentage(self):
        """Calcul du pourcentage de progression."""
        expedition = Expedition.objects.create(
            user=self.user,
            nom_article='Test',
            direction='FR_DZ'
        )

        # 0 etapes terminees = 0%
        self.assertEqual(expedition.get_progress_percentage(), 0)

        # Terminer etape 1
        etape1 = expedition.get_etape(1)
        etape1.marquer_termine()

        # 1 etape terminee = 20%
        self.assertEqual(expedition.get_progress_percentage(), 20)


class ExpeditionEtapeModelTestCase(TestCase):
    """Tests pour le modele ExpeditionEtape."""

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

    def test_etape_created_with_correct_type(self):
        """Les etapes ont le bon type."""
        types_attendus = {
            1: 'classification',
            2: 'documents',
            3: 'transmission',
            4: 'paiement',
            5: 'oea'
        }

        for numero, type_attendu in types_attendus.items():
            etape = self.expedition.get_etape(numero)
            self.assertEqual(etape.type_etape, type_attendu)

    def test_etape_initial_status(self):
        """Statut initial des etapes."""
        etape1 = self.expedition.get_etape(1)
        self.assertEqual(etape1.statut, 'en_cours')

        for i in range(2, 6):
            etape = self.expedition.get_etape(i)
            self.assertEqual(etape.statut, 'en_attente')

    def test_marquer_termine(self):
        """Marquer une etape comme terminee."""
        etape = self.expedition.get_etape(1)
        etape.marquer_termine()

        self.assertEqual(etape.statut, 'termine')
        self.assertIsNotNone(etape.completed_at)

    def test_marquer_termine_active_next_etape(self):
        """Terminer une etape active la suivante."""
        etape1 = self.expedition.get_etape(1)
        etape2 = self.expedition.get_etape(2)

        self.assertEqual(etape2.statut, 'en_attente')

        etape1.marquer_termine()
        etape2.refresh_from_db()

        self.assertEqual(etape2.statut, 'en_cours')

    def test_get_data_returns_correct_type(self):
        """get_data() retourne le bon type de donnees."""
        data_types = {
            1: ClassificationData,
            2: DocumentsData,
            3: TransmissionData,
            4: PaiementData,
            5: OEAData
        }

        for numero, data_class in data_types.items():
            etape = self.expedition.get_etape(numero)
            data = etape.get_data()
            self.assertIsInstance(data, data_class)

    def test_unique_together_expedition_numero(self):
        """Une seule etape par numero par expedition."""
        with self.assertRaises(IntegrityError):
            ExpeditionEtape.objects.create(
                expedition=self.expedition,
                numero=1,
                type_etape='classification'
            )


class ClassificationDataModelTestCase(TestCase):
    """Tests pour le modele ClassificationData."""

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

    def test_initial_values(self):
        """Valeurs initiales."""
        self.assertIsNone(self.classification_data.code_sh)
        self.assertIsNone(self.classification_data.code_nc)
        self.assertIsNone(self.classification_data.code_taric)
        self.assertEqual(self.classification_data.chat_historique, [])
        self.assertEqual(self.classification_data.propositions, [])
        self.assertIsNone(self.classification_data.proposition_selectionnee)

    def test_save_codes(self):
        """Sauvegarder les codes."""
        self.classification_data.code_sh = '847130'
        self.classification_data.code_nc = '84713000'
        self.classification_data.code_taric = '8471300000'
        self.classification_data.save()

        # Recharger depuis la BDD
        self.classification_data.refresh_from_db()

        self.assertEqual(self.classification_data.code_sh, '847130')
        self.assertEqual(self.classification_data.code_nc, '84713000')
        self.assertEqual(self.classification_data.code_taric, '8471300000')

    def test_add_message_to_chat(self):
        """Ajouter un message au chat."""
        self.classification_data.add_message(
            role='user',
            content='Mon produit est un ordinateur portable'
        )

        self.assertEqual(len(self.classification_data.chat_historique), 1)
        msg = self.classification_data.chat_historique[0]
        self.assertEqual(msg['role'], 'user')
        self.assertEqual(msg['content'], 'Mon produit est un ordinateur portable')
        self.assertIn('timestamp', msg)

    def test_set_propositions(self):
        """Definir les propositions TARIC."""
        propositions = [
            {
                'code_taric': '8471300000',
                'code_nc': '84713000',
                'code_sh': '847130',
                'probability': 85,
                'description': 'Ordinateurs portables',
                'justification': 'Basé sur la description'
            },
            {
                'code_taric': '8471410000',
                'code_nc': '84714100',
                'code_sh': '847141',
                'probability': 65,
                'description': 'Autres machines automatiques',
                'justification': 'Alternative possible'
            }
        ]

        self.classification_data.set_propositions(propositions)

        self.assertEqual(len(self.classification_data.propositions), 2)
        self.assertEqual(self.classification_data.propositions[0]['probability'], 85)

    def test_select_proposition(self):
        """Selectionner une proposition."""
        propositions = [
            {'code_taric': '8471300000', 'probability': 85},
            {'code_taric': '8471410000', 'probability': 65}
        ]
        self.classification_data.set_propositions(propositions)
        self.classification_data.select_proposition(0)

        self.assertEqual(self.classification_data.proposition_selectionnee, 0)

    def test_selected_proposal_property(self):
        """Propriete selected_proposal."""
        propositions = [
            {'code_taric': '8471300000', 'probability': 85},
            {'code_taric': '8471410000', 'probability': 65}
        ]
        self.classification_data.set_propositions(propositions)
        self.classification_data.select_proposition(1)

        selected = self.classification_data.selected_proposal
        self.assertEqual(selected['code_taric'], '8471410000')

    def test_validate_classification(self):
        """Valider la classification."""
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

    def test_formatted_code_property(self):
        """Propriete formatted_code."""
        self.classification_data.code_taric = '8471300000'
        self.classification_data.save()

        formatted = self.classification_data.formatted_code
        self.assertEqual(formatted, '8471.30.00.00')


class ExpeditionDocumentModelTestCase(TestCase):
    """Tests pour le modele ExpeditionDocument."""

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

    def test_create_document(self):
        """Creer un document."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        test_file = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'fake image content',
            content_type='image/jpeg'
        )

        document = ExpeditionDocument.objects.create(
            etape=self.etape,
            type='photo',
            fichier=test_file,
            nom_original='test_image.jpg'
        )

        self.assertIsNotNone(document.id)
        self.assertEqual(document.type, 'photo')
        self.assertEqual(document.nom_original, 'test_image.jpg')

    def test_is_image_property(self):
        """Propriete is_image."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Image
        image_file = SimpleUploadedFile('test.jpg', b'content', 'image/jpeg')
        image_doc = ExpeditionDocument.objects.create(
            etape=self.etape,
            type='photo',
            fichier=image_file,
            nom_original='test.jpg'
        )
        self.assertTrue(image_doc.is_image)

        # PDF
        pdf_file = SimpleUploadedFile('test.pdf', b'content', 'application/pdf')
        pdf_doc = ExpeditionDocument.objects.create(
            etape=self.etape,
            type='fiche_technique',
            fichier=pdf_file,
            nom_original='test.pdf'
        )
        self.assertFalse(pdf_doc.is_image)

    def test_document_ordering(self):
        """Ordre des documents."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        file1 = SimpleUploadedFile('1.jpg', b'c', 'image/jpeg')
        file2 = SimpleUploadedFile('2.jpg', b'c', 'image/jpeg')

        doc1 = ExpeditionDocument.objects.create(
            etape=self.etape,
            type='photo',
            fichier=file1,
            nom_original='first.jpg',
            ordre=2
        )
        doc2 = ExpeditionDocument.objects.create(
            etape=self.etape,
            type='photo',
            fichier=file2,
            nom_original='second.jpg',
            ordre=1
        )

        docs = self.etape.documents.filter(type='photo').order_by('ordre')
        self.assertEqual(docs[0].nom_original, 'second.jpg')
        self.assertEqual(docs[1].nom_original, 'first.jpg')


class DataTablesRelationsTestCase(TestCase):
    """Tests pour les relations entre tables de donnees."""

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

    def test_one_to_one_classification_data(self):
        """Relation 1:1 ClassificationData."""
        etape = self.expedition.get_etape(1)

        # Doit avoir exactement un ClassificationData
        self.assertEqual(
            ClassificationData.objects.filter(etape=etape).count(),
            1
        )

    def test_one_to_one_all_data_tables(self):
        """Toutes les tables de donnees sont en 1:1."""
        self.assertEqual(ClassificationData.objects.count(), 1)
        self.assertEqual(DocumentsData.objects.count(), 1)
        self.assertEqual(TransmissionData.objects.count(), 1)
        self.assertEqual(PaiementData.objects.count(), 1)
        self.assertEqual(OEAData.objects.count(), 1)

    def test_cascade_delete(self):
        """Suppression en cascade."""
        expedition_id = self.expedition.id

        # Verifier que les donnees existent
        self.assertTrue(ExpeditionEtape.objects.filter(expedition_id=expedition_id).exists())
        self.assertTrue(ClassificationData.objects.exists())

        # Supprimer l'expedition
        self.expedition.delete()

        # Tout devrait etre supprime
        self.assertFalse(ExpeditionEtape.objects.filter(expedition_id=expedition_id).exists())
        self.assertFalse(ClassificationData.objects.exists())
        self.assertFalse(DocumentsData.objects.exists())
