"""
Tests pour l'upload et la gestion des documents.
- Upload de fichiers (photos, PDFs)
- Association aux etapes
- Validation des types
- Suppression
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
import json

from apps.expeditions.models import (
    Expedition, ExpeditionEtape, ExpeditionDocument,
    ClassificationData
)

User = get_user_model()


class DocumentUploadTestCase(TestCase):
    """Tests pour l'upload de documents."""

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
            nom_article='Laptop Dell',
            description='Ordinateur portable',
            direction='FR_DZ'
        )
        self.etape = self.expedition.get_etape(1)

    def test_upload_image_jpg(self):
        """Upload d'une image JPEG."""
        image_content = b'\xff\xd8\xff\xe0\x00\x10JFIF'  # JPEG header
        image = SimpleUploadedFile(
            name='photo.jpg',
            content=image_content,
            content_type='image/jpeg'
        )

        doc = ExpeditionDocument.objects.create(
            etape=self.etape,
            type='photo',
            fichier=image,
            nom_original='photo.jpg'
        )

        self.assertIsNotNone(doc.id)
        self.assertEqual(doc.type, 'photo')
        self.assertTrue(doc.is_image)

    def test_upload_image_png(self):
        """Upload d'une image PNG."""
        png_content = b'\x89PNG\r\n\x1a\n'  # PNG header
        image = SimpleUploadedFile(
            name='photo.png',
            content=png_content,
            content_type='image/png'
        )

        doc = ExpeditionDocument.objects.create(
            etape=self.etape,
            type='photo',
            fichier=image,
            nom_original='photo.png'
        )

        self.assertTrue(doc.is_image)

    def test_upload_pdf(self):
        """Upload d'un fichier PDF."""
        pdf_content = b'%PDF-1.4 fake pdf content'
        pdf = SimpleUploadedFile(
            name='fiche_technique.pdf',
            content=pdf_content,
            content_type='application/pdf'
        )

        doc = ExpeditionDocument.objects.create(
            etape=self.etape,
            type='fiche_technique',
            fichier=pdf,
            nom_original='fiche_technique.pdf'
        )

        self.assertIsNotNone(doc.id)
        self.assertEqual(doc.type, 'fiche_technique')
        self.assertFalse(doc.is_image)

    def test_upload_multiple_files(self):
        """Upload de plusieurs fichiers."""
        for i in range(3):
            image = SimpleUploadedFile(
                name=f'photo_{i}.jpg',
                content=b'fake image content',
                content_type='image/jpeg'
            )
            ExpeditionDocument.objects.create(
                etape=self.etape,
                type='photo',
                fichier=image,
                nom_original=f'photo_{i}.jpg',
                ordre=i
            )

        self.assertEqual(self.etape.documents.count(), 3)

    def test_document_ordering(self):
        """Ordre des documents."""
        file1 = SimpleUploadedFile('1.jpg', b'c', 'image/jpeg')
        file2 = SimpleUploadedFile('2.jpg', b'c', 'image/jpeg')
        file3 = SimpleUploadedFile('3.jpg', b'c', 'image/jpeg')

        doc3 = ExpeditionDocument.objects.create(
            etape=self.etape, type='photo', fichier=file1,
            nom_original='third.jpg', ordre=3
        )
        doc1 = ExpeditionDocument.objects.create(
            etape=self.etape, type='photo', fichier=file2,
            nom_original='first.jpg', ordre=1
        )
        doc2 = ExpeditionDocument.objects.create(
            etape=self.etape, type='photo', fichier=file3,
            nom_original='second.jpg', ordre=2
        )

        docs = self.etape.documents.order_by('ordre')
        self.assertEqual(docs[0].nom_original, 'first.jpg')
        self.assertEqual(docs[1].nom_original, 'second.jpg')
        self.assertEqual(docs[2].nom_original, 'third.jpg')


class DocumentAssociationTestCase(TestCase):
    """Tests pour l'association documents-etapes."""

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

    def test_document_linked_to_correct_etape(self):
        """Document associe a la bonne etape."""
        etape1 = self.expedition.get_etape(1)
        etape2 = self.expedition.get_etape(2)

        file1 = SimpleUploadedFile('doc1.pdf', b'c', 'application/pdf')
        file2 = SimpleUploadedFile('doc2.pdf', b'c', 'application/pdf')

        doc1 = ExpeditionDocument.objects.create(
            etape=etape1,
            type='fiche_technique',
            fichier=file1,
            nom_original='doc_etape1.pdf'
        )
        doc2 = ExpeditionDocument.objects.create(
            etape=etape2,
            type='facture',
            fichier=file2,
            nom_original='doc_etape2.pdf'
        )

        self.assertEqual(etape1.documents.count(), 1)
        self.assertEqual(etape2.documents.count(), 1)
        self.assertEqual(etape1.documents.first().nom_original, 'doc_etape1.pdf')

    def test_documents_per_expedition(self):
        """Documents groupes par expedition."""
        exp2 = Expedition.objects.create(
            user=self.user,
            nom_article='Test 2',
            direction='DZ_FR'
        )

        etape1_exp1 = self.expedition.get_etape(1)
        etape1_exp2 = exp2.get_etape(1)

        file1 = SimpleUploadedFile('exp1.pdf', b'c', 'application/pdf')
        file2 = SimpleUploadedFile('exp2.pdf', b'c', 'application/pdf')

        ExpeditionDocument.objects.create(
            etape=etape1_exp1,
            type='photo',
            fichier=file1,
            nom_original='exp1.pdf'
        )
        ExpeditionDocument.objects.create(
            etape=etape1_exp2,
            type='photo',
            fichier=file2,
            nom_original='exp2.pdf'
        )

        # Chaque expedition a son propre document
        self.assertEqual(etape1_exp1.documents.count(), 1)
        self.assertEqual(etape1_exp2.documents.count(), 1)


class DocumentDeletionTestCase(TestCase):
    """Tests pour la suppression de documents."""

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

    def test_delete_single_document(self):
        """Supprimer un document."""
        file = SimpleUploadedFile('test.pdf', b'c', 'application/pdf')
        doc = ExpeditionDocument.objects.create(
            etape=self.etape,
            type='photo',
            fichier=file,
            nom_original='test.pdf'
        )

        doc_id = doc.id
        doc.delete()

        self.assertFalse(ExpeditionDocument.objects.filter(id=doc_id).exists())

    def test_cascade_delete_on_etape_delete(self):
        """Documents supprimes avec l'etape."""
        file = SimpleUploadedFile('test.pdf', b'c', 'application/pdf')
        ExpeditionDocument.objects.create(
            etape=self.etape,
            type='photo',
            fichier=file,
            nom_original='test.pdf'
        )

        etape_id = self.etape.id
        self.etape.delete()

        self.assertFalse(
            ExpeditionDocument.objects.filter(etape_id=etape_id).exists()
        )

    def test_cascade_delete_on_expedition_delete(self):
        """Documents supprimes avec l'expedition."""
        etape = self.expedition.get_etape(1)
        file = SimpleUploadedFile('test.pdf', b'c', 'application/pdf')
        ExpeditionDocument.objects.create(
            etape=etape,
            type='photo',
            fichier=file,
            nom_original='test.pdf'
        )

        self.assertEqual(ExpeditionDocument.objects.count(), 1)

        self.expedition.delete()

        self.assertEqual(ExpeditionDocument.objects.count(), 0)


class DocumentTypesTestCase(TestCase):
    """Tests pour les differents types de documents."""

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

    def test_document_types_etape_1(self):
        """Types de documents pour etape 1 (classification)."""
        types = ['photo', 'fiche_technique']

        for doc_type in types:
            file = SimpleUploadedFile(f'{doc_type}.pdf', b'c', 'application/pdf')
            doc = ExpeditionDocument.objects.create(
                etape=self.etape,
                type=doc_type,
                fichier=file,
                nom_original=f'{doc_type}.pdf'
            )
            self.assertEqual(doc.type, doc_type)

    def test_filter_documents_by_type(self):
        """Filtrer documents par type."""
        file1 = SimpleUploadedFile('photo.jpg', b'c', 'image/jpeg')
        file2 = SimpleUploadedFile('tech.pdf', b'c', 'application/pdf')
        file3 = SimpleUploadedFile('photo2.jpg', b'c', 'image/jpeg')

        ExpeditionDocument.objects.create(
            etape=self.etape, type='photo',
            fichier=file1, nom_original='photo1.jpg'
        )
        ExpeditionDocument.objects.create(
            etape=self.etape, type='fiche_technique',
            fichier=file2, nom_original='tech.pdf'
        )
        ExpeditionDocument.objects.create(
            etape=self.etape, type='photo',
            fichier=file3, nom_original='photo2.jpg'
        )

        photos = self.etape.documents.filter(type='photo')
        fiches = self.etape.documents.filter(type='fiche_technique')

        self.assertEqual(photos.count(), 2)
        self.assertEqual(fiches.count(), 1)


class ClassificationUploadViewTestCase(TestCase):
    """Tests pour la vue d'upload de classification."""

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
            nom_article='Laptop',
            direction='FR_DZ'
        )

    def test_classification_page_accessible(self):
        """Page de classification accessible."""
        url = reverse(
            'apps_expeditions:classification',
            kwargs={'pk': self.expedition.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_classification_shows_expedition_info(self):
        """Page affiche les infos de l'expedition."""
        url = reverse(
            'apps_expeditions:classification',
            kwargs={'pk': self.expedition.pk}
        )
        response = self.client.get(url)

        self.assertContains(response, self.expedition.reference)

