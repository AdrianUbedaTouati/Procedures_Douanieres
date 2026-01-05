"""
Modeles pour le module Expeditions.
Structure: Expedition -> ExpeditionEtape (1:5) -> *Data (1:1 par type)

Voir docs/DATABASE_SCHEMA.md pour la documentation complete.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def document_upload_path(instance, filename):
    """
    Genere le chemin d'upload pour les documents.
    Format: {exp_id}/etape_{n}_{type}/{images|documents}/{filename}
    Note: MEDIA_ROOT est data/media_expediciones/ donc pas besoin du prefixe
    """
    etape = instance.etape
    exp_id = etape.expedition_id

    # Determiner le sous-dossier selon le type de fichier
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        subfolder = 'images'
    else:
        subfolder = 'documents'

    return f'{exp_id}/etape_{etape.numero}_{etape.type_etape}/{subfolder}/{filename}'


# =============================================================================
# MODELE PRINCIPAL: EXPEDITION
# =============================================================================

class Expedition(models.Model):
    """
    Un article/envoi en cours de traitement douanier.
    Represente une expedition avec ses 5 etapes du processus douanier.
    """

    DIRECTIONS = [
        ('FR_DZ', 'France -> Algerie'),
        ('DZ_FR', 'Algerie -> France'),
    ]

    STATUTS = [
        ('brouillon', 'Brouillon'),
        ('en_cours', 'En cours'),
        ('termine', 'Termine'),
        ('erreur', 'Erreur'),
    ]

    reference = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Reference",
        help_text="Identifiant unique de l'expedition (ex: EXP-2025-001)"
    )
    nom_article = models.CharField(
        max_length=255,
        verbose_name="Nom de l'article",
        help_text="Nom descriptif du produit"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Description detaillee du produit"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='expeditions',
        verbose_name="Utilisateur"
    )
    direction = models.CharField(
        max_length=10,
        choices=DIRECTIONS,
        default='FR_DZ',
        verbose_name="Direction"
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default='brouillon',
        verbose_name="Statut"
    )
    etape_courante = models.IntegerField(
        default=1,
        verbose_name="Etape courante",
        help_text="Numero de l'etape en cours (1-5)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Cree le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifie le")

    class Meta:
        verbose_name = "Expedition"
        verbose_name_plural = "Expeditions"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.nom_article}"

    def save(self, *args, **kwargs):
        # Generer une reference automatique si non fournie
        if not self.reference:
            year = timezone.now().year
            last_exp = Expedition.objects.filter(
                reference__startswith=f'EXP-{year}-'
            ).order_by('-reference').first()

            if last_exp:
                last_num = int(last_exp.reference.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1

            self.reference = f'EXP-{year}-{new_num:03d}'

        super().save(*args, **kwargs)

        # Creer les 5 etapes si elles n'existent pas
        if not self.etapes.exists():
            self._create_etapes()

    def _create_etapes(self):
        """Cree les 5 etapes avec leurs tables de donnees associees."""
        etape_types = {
            1: 'classification',
            2: 'documents',
            3: 'transmission',
            4: 'paiement',
            5: 'oea',
        }

        for numero in range(1, 6):
            etape = ExpeditionEtape.objects.create(
                expedition=self,
                numero=numero,
                type_etape=etape_types[numero],
                statut='en_attente' if numero > 1 else 'en_cours'
            )

            # Creer la table de donnees specifique
            if numero == 1:
                ClassificationData.objects.create(etape=etape)
            elif numero == 2:
                DocumentsData.objects.create(etape=etape)
            elif numero == 3:
                TransmissionData.objects.create(etape=etape)
            elif numero == 4:
                PaiementData.objects.create(etape=etape)
            elif numero == 5:
                OEAData.objects.create(etape=etape)

    def get_etape(self, numero: int):
        """Recupere une etape specifique."""
        return self.etapes.filter(numero=numero).first()

    def get_progress_percentage(self) -> int:
        """Calcule le pourcentage de progression."""
        etapes_terminees = self.etapes.filter(statut='termine').count()
        return int((etapes_terminees / 5) * 100)


# =============================================================================
# MODELE INTERMEDIAIRE: EXPEDITION ETAPE
# =============================================================================

class ExpeditionEtape(models.Model):
    """
    Une etape du processus douanier.
    Table intermediaire avec les champs communs a toutes les etapes.
    Chaque etape a une relation 1:1 avec sa table de donnees specifique.
    """

    ETAPES = [
        (1, 'Classification Douaniere'),
        (2, 'Generation Documents'),
        (3, 'Transmission Electronique'),
        (4, 'Paiement des Droits'),
        (5, 'Gestion OEA'),
    ]

    TYPE_ETAPES = [
        ('classification', 'Classification'),
        ('documents', 'Documents'),
        ('transmission', 'Transmission'),
        ('paiement', 'Paiement'),
        ('oea', 'OEA'),
    ]

    ETAPES_DESCRIPTION = {
        1: "Identification des codes SH/NC/TARIC par IA",
        2: "Generation des documents DAU, D10, D12",
        3: "Transmission vers DELTA ou BADR",
        4: "Calcul et paiement des droits de douane",
        5: "Gestion du statut OEA",
    }

    STATUTS_ETAPE = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('termine', 'Termine'),
        ('erreur', 'Erreur'),
    ]

    expedition = models.ForeignKey(
        Expedition,
        on_delete=models.CASCADE,
        related_name='etapes',
        verbose_name="Expedition"
    )
    numero = models.IntegerField(
        choices=ETAPES,
        verbose_name="Numero d'etape"
    )
    type_etape = models.CharField(
        max_length=20,
        choices=TYPE_ETAPES,
        default='classification',
        verbose_name="Type d'etape"
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUTS_ETAPE,
        default='en_attente',
        verbose_name="Statut"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Termine le"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Etape d'expedition"
        verbose_name_plural = "Etapes d'expedition"
        ordering = ['expedition', 'numero']
        unique_together = ['expedition', 'numero']

    def __str__(self):
        return f"{self.expedition.reference} - Etape {self.numero}: {self.get_numero_display()}"

    @property
    def nom(self):
        """Retourne le nom de l'etape."""
        return dict(self.ETAPES).get(self.numero, "Inconnu")

    @property
    def description(self):
        """Retourne la description de l'etape."""
        return self.ETAPES_DESCRIPTION.get(self.numero, "")

    @property
    def icone(self):
        """Retourne l'icone Bootstrap correspondante."""
        icones = {
            1: 'bi-tags',
            2: 'bi-file-earmark-text',
            3: 'bi-cloud-upload',
            4: 'bi-calculator',
            5: 'bi-award',
        }
        return icones.get(self.numero, 'bi-circle')

    @property
    def couleur(self):
        """Retourne la couleur Bootstrap correspondante."""
        couleurs = {
            1: 'primary',
            2: 'success',
            3: 'info',
            4: 'warning',
            5: 'secondary',
        }
        return couleurs.get(self.numero, 'secondary')

    def get_data(self):
        """Retourne les donnees specifiques de l'etape."""
        if self.numero == 1:
            return getattr(self, 'classification_data', None)
        elif self.numero == 2:
            return getattr(self, 'documents_data', None)
        elif self.numero == 3:
            return getattr(self, 'transmission_data', None)
        elif self.numero == 4:
            return getattr(self, 'paiement_data', None)
        elif self.numero == 5:
            return getattr(self, 'oea_data', None)
        return None

    def marquer_termine(self, donnees: dict = None):
        """Marque l'etape comme terminee et passe a la suivante."""
        self.statut = 'termine'
        self.completed_at = timezone.now()
        self.save()

        # Mettre a jour l'expedition
        self.expedition.etape_courante = min(self.numero + 1, 5)

        # Si toutes les etapes sont terminees
        if self.numero == 5:
            self.expedition.statut = 'termine'
        else:
            # Passer l'etape suivante en cours
            etape_suivante = self.expedition.get_etape(self.numero + 1)
            if etape_suivante:
                etape_suivante.statut = 'en_cours'
                etape_suivante.save()

        self.expedition.save()


# =============================================================================
# DONNEES SPECIFIQUES: ETAPE 1 - CLASSIFICATION
# =============================================================================

class ClassificationData(models.Model):
    """
    Donnees specifiques a l'etape 1: Classification Douaniere.
    Contient les codes TARIC et l'historique du chat.
    """

    etape = models.OneToOneField(
        ExpeditionEtape,
        on_delete=models.CASCADE,
        related_name='classification_data',
        verbose_name="Etape"
    )

    # Codes TARIC valides
    code_sh = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        verbose_name="Code SH (6 chiffres)"
    )
    code_nc = models.CharField(
        max_length=8,
        blank=True,
        null=True,
        verbose_name="Code NC (8 chiffres)"
    )
    code_taric = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Code TARIC (10 chiffres)"
    )

    # Historique du chat (simplifie)
    chat_historique = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Historique du chat",
        help_text="Liste des messages [{role, content, timestamp}, ...]"
    )

    # Propositions TARIC
    propositions = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Propositions TARIC",
        help_text="Liste des propositions [{code_taric, probability, description, justification}, ...]"
    )

    # Index de la proposition selectionnee
    proposition_selectionnee = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Proposition selectionnee",
        help_text="Index de la proposition choisie dans la liste"
    )

    class Meta:
        verbose_name = "Donnees Classification"
        verbose_name_plural = "Donnees Classification"

    def __str__(self):
        return f"Classification - {self.etape.expedition.reference}"

    @property
    def formatted_code(self):
        """Retourne le code TARIC formate avec des points."""
        if self.code_taric and len(self.code_taric) == 10:
            c = self.code_taric
            return f"{c[:4]}.{c[4:6]}.{c[6:8]}.{c[8:]}"
        return self.code_taric or ""

    @property
    def selected_proposal(self):
        """Retourne la proposition selectionnee."""
        if self.proposition_selectionnee is not None and self.propositions:
            if 0 <= self.proposition_selectionnee < len(self.propositions):
                return self.propositions[self.proposition_selectionnee]
        return None

    def add_message(self, role: str, content: str):
        """Ajoute un message a l'historique du chat."""
        message = {
            'role': role,
            'content': content,
            'timestamp': timezone.now().isoformat()
        }
        self.chat_historique.append(message)
        self.save(update_fields=['chat_historique'])
        return message

    def set_propositions(self, propositions: list):
        """Definit les propositions TARIC."""
        self.propositions = propositions
        self.proposition_selectionnee = None
        self.save(update_fields=['propositions', 'proposition_selectionnee'])

    def select_proposition(self, index: int):
        """Selectionne une proposition par son index."""
        if 0 <= index < len(self.propositions):
            self.proposition_selectionnee = index
            self.save(update_fields=['proposition_selectionnee'])
            return True
        return False

    def validate_classification(self):
        """Valide la classification avec la proposition selectionnee."""
        proposal = self.selected_proposal
        if proposal:
            self.code_sh = proposal.get('code_sh', '')[:6]
            self.code_nc = proposal.get('code_nc', '')[:8]
            self.code_taric = proposal.get('code_taric', '')[:10]
            self.save(update_fields=['code_sh', 'code_nc', 'code_taric'])
            return True
        return False


# =============================================================================
# DONNEES SPECIFIQUES: ETAPE 2 - DOCUMENTS (PLACEHOLDER)
# =============================================================================

class DocumentsData(models.Model):
    """
    Donnees specifiques a l'etape 2: Generation de Documents.
    Placeholder pour developpement futur.
    """

    etape = models.OneToOneField(
        ExpeditionEtape,
        on_delete=models.CASCADE,
        related_name='documents_data',
        verbose_name="Etape"
    )

    dau_genere = models.BooleanField(default=False, verbose_name="DAU genere")
    d10_genere = models.BooleanField(default=False, verbose_name="D10 genere")
    d12_genere = models.BooleanField(default=False, verbose_name="D12 genere")

    class Meta:
        verbose_name = "Donnees Documents"
        verbose_name_plural = "Donnees Documents"

    def __str__(self):
        return f"Documents - {self.etape.expedition.reference}"


# =============================================================================
# DONNEES SPECIFIQUES: ETAPE 3 - TRANSMISSION (PLACEHOLDER)
# =============================================================================

class TransmissionData(models.Model):
    """
    Donnees specifiques a l'etape 3: Transmission Electronique.
    Placeholder pour developpement futur.
    """

    etape = models.OneToOneField(
        ExpeditionEtape,
        on_delete=models.CASCADE,
        related_name='transmission_data',
        verbose_name="Etape"
    )

    systeme_cible = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Systeme cible",
        help_text="DELTA ou BADR"
    )
    reference_transmission = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Reference transmission"
    )
    date_transmission = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de transmission"
    )

    class Meta:
        verbose_name = "Donnees Transmission"
        verbose_name_plural = "Donnees Transmission"

    def __str__(self):
        return f"Transmission - {self.etape.expedition.reference}"


# =============================================================================
# DONNEES SPECIFIQUES: ETAPE 4 - PAIEMENT (PLACEHOLDER)
# =============================================================================

class PaiementData(models.Model):
    """
    Donnees specifiques a l'etape 4: Paiement des Droits.
    Placeholder pour developpement futur.
    """

    etape = models.OneToOneField(
        ExpeditionEtape,
        on_delete=models.CASCADE,
        related_name='paiement_data',
        verbose_name="Etape"
    )

    montant_droits = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montant des droits"
    )
    montant_tva = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montant TVA"
    )
    reference_paiement = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Reference paiement"
    )
    date_paiement = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de paiement"
    )

    class Meta:
        verbose_name = "Donnees Paiement"
        verbose_name_plural = "Donnees Paiement"

    def __str__(self):
        return f"Paiement - {self.etape.expedition.reference}"


# =============================================================================
# DONNEES SPECIFIQUES: ETAPE 5 - OEA (PLACEHOLDER)
# =============================================================================

class OEAData(models.Model):
    """
    Donnees specifiques a l'etape 5: Gestion OEA.
    Placeholder pour developpement futur.
    """

    etape = models.OneToOneField(
        ExpeditionEtape,
        on_delete=models.CASCADE,
        related_name='oea_data',
        verbose_name="Etape"
    )

    statut_oea = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Statut OEA"
    )
    numero_certificat = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Numero certificat"
    )

    class Meta:
        verbose_name = "Donnees OEA"
        verbose_name_plural = "Donnees OEA"

    def __str__(self):
        return f"OEA - {self.etape.expedition.reference}"


# =============================================================================
# DOCUMENTS D'EXPEDITION
# =============================================================================

class ExpeditionDocument(models.Model):
    """
    Document associe a une etape d'expedition.
    Peut etre une photo du produit, une fiche technique, ou un document genere.
    """

    TYPES = [
        ('photo', 'Photo du produit'),
        ('fiche_technique', 'Fiche technique'),
        ('dau', 'DAU - Document Administratif Unique'),
        ('d10', 'Formulaire D10'),
        ('d12', 'Formulaire D12'),
        ('ens', 'ENS - Entry Summary Declaration'),
        ('certificat_origine', "Certificat d'origine"),
        ('autre', 'Autre document'),
    ]

    etape = models.ForeignKey(
        ExpeditionEtape,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name="Etape"
    )
    type = models.CharField(
        max_length=30,
        choices=TYPES,
        verbose_name="Type de document"
    )
    fichier = models.FileField(
        upload_to=document_upload_path,
        verbose_name="Fichier"
    )
    nom_original = models.CharField(
        max_length=255,
        verbose_name="Nom original",
        help_text="Nom du fichier tel qu'uploade"
    )
    ordre = models.IntegerField(
        default=0,
        verbose_name="Ordre",
        help_text="Ordre d'affichage du document"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Cree le")

    class Meta:
        verbose_name = "Document d'expedition"
        verbose_name_plural = "Documents d'expedition"
        ordering = ['type', 'ordre', '-created_at']

    def __str__(self):
        return f"{self.etape.expedition.reference} - {self.get_type_display()}"

    @property
    def expedition(self):
        """Raccourci pour acceder a l'expedition."""
        return self.etape.expedition

    @property
    def extension(self):
        """Retourne l'extension du fichier."""
        return self.nom_original.split('.')[-1].lower() if '.' in self.nom_original else ''

    @property
    def is_image(self):
        """Verifie si le document est une image."""
        return self.extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']

    @property
    def is_pdf(self):
        """Verifie si le document est un PDF."""
        return self.extension == 'pdf'
