from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Expedition(models.Model):
    """
    Un article/envoi en cours de traitement douanier.
    Représente une expédition avec ses 5 étapes du processus douanier.
    """

    DIRECTIONS = [
        ('FR_DZ', 'France → Algérie'),
        ('DZ_FR', 'Algérie → France'),
    ]

    STATUTS = [
        ('brouillon', 'Brouillon'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('erreur', 'Erreur'),
    ]

    reference = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Référence",
        help_text="Identifiant unique de l'expédition (ex: EXP-2025-001)"
    )
    nom_article = models.CharField(
        max_length=255,
        verbose_name="Nom de l'article",
        help_text="Nom descriptif du produit"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Description détaillée du produit"
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
        verbose_name="Étape courante",
        help_text="Numéro de l'étape en cours (1-5)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    class Meta:
        verbose_name = "Expédition"
        verbose_name_plural = "Expéditions"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.nom_article}"

    def save(self, *args, **kwargs):
        # Générer une référence automatique si non fournie
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

        # Créer les 5 étapes si elles n'existent pas
        if not self.etapes.exists():
            for numero in range(1, 6):
                ExpeditionEtape.objects.create(
                    expedition=self,
                    numero=numero,
                    statut='en_attente' if numero > 1 else 'en_cours'
                )

    def get_etape(self, numero: int):
        """Récupère une étape spécifique."""
        return self.etapes.filter(numero=numero).first()

    def get_progress_percentage(self) -> int:
        """Calcule le pourcentage de progression."""
        etapes_terminees = self.etapes.filter(statut='termine').count()
        return int((etapes_terminees / 5) * 100)


class ExpeditionEtape(models.Model):
    """
    Une étape du processus douanier.
    Chaque expédition a exactement 5 étapes fixes.
    """

    ETAPES = [
        (1, 'Classification Douanière'),
        (2, 'Génération Documents'),
        (3, 'Transmission Électronique'),
        (4, 'Paiement des Droits'),
        (5, 'Gestion OEA'),
    ]

    ETAPES_DESCRIPTION = {
        1: "Identification des codes SH/NC/TARIC par IA",
        2: "Génération des documents DAU, D10, D12",
        3: "Transmission vers DELTA ou BADR",
        4: "Calcul et paiement des droits de douane",
        5: "Gestion du statut OEA",
    }

    STATUTS_ETAPE = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('erreur', 'Erreur'),
    ]

    expedition = models.ForeignKey(
        Expedition,
        on_delete=models.CASCADE,
        related_name='etapes',
        verbose_name="Expédition"
    )
    numero = models.IntegerField(
        choices=ETAPES,
        verbose_name="Numéro d'étape"
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUTS_ETAPE,
        default='en_attente',
        verbose_name="Statut"
    )
    donnees = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Données",
        help_text="Résultats et données de l'étape (JSON)"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Terminé le"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Étape d'expédition"
        verbose_name_plural = "Étapes d'expédition"
        ordering = ['expedition', 'numero']
        unique_together = ['expedition', 'numero']

    def __str__(self):
        return f"{self.expedition.reference} - Étape {self.numero}: {self.get_numero_display()}"

    @property
    def nom(self):
        """Retourne le nom de l'étape."""
        return dict(self.ETAPES).get(self.numero, "Inconnu")

    @property
    def description(self):
        """Retourne la description de l'étape."""
        return self.ETAPES_DESCRIPTION.get(self.numero, "")

    @property
    def icone(self):
        """Retourne l'icône Bootstrap correspondante."""
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

    def marquer_termine(self, donnees: dict = None):
        """Marque l'étape comme terminée et passe à la suivante."""
        self.statut = 'termine'
        self.completed_at = timezone.now()
        if donnees:
            self.donnees = donnees
        self.save()

        # Mettre à jour l'expédition
        self.expedition.etape_courante = min(self.numero + 1, 5)

        # Si toutes les étapes sont terminées
        if self.numero == 5:
            self.expedition.statut = 'termine'
        else:
            # Passer l'étape suivante en cours
            etape_suivante = self.expedition.get_etape(self.numero + 1)
            if etape_suivante:
                etape_suivante.statut = 'en_cours'
                etape_suivante.save()

        self.expedition.save()


class ExpeditionDocument(models.Model):
    """
    Document associé à une expédition.
    Peut être une photo du produit, une fiche technique, ou un document généré.
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

    expedition = models.ForeignKey(
        Expedition,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name="Expédition"
    )
    type = models.CharField(
        max_length=30,
        choices=TYPES,
        verbose_name="Type de document"
    )
    fichier = models.FileField(
        upload_to='expeditions/documents/%Y/%m/',
        verbose_name="Fichier"
    )
    nom_original = models.CharField(
        max_length=255,
        verbose_name="Nom original",
        help_text="Nom du fichier tel qu'uploadé"
    )
    etape = models.ForeignKey(
        ExpeditionEtape,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name="Étape associée"
    )
    ordre = models.IntegerField(
        default=0,
        verbose_name="Ordre",
        help_text="Ordre d'affichage du document"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")

    class Meta:
        verbose_name = "Document d'expédition"
        verbose_name_plural = "Documents d'expédition"
        ordering = ['type', 'ordre', '-created_at']

    def __str__(self):
        return f"{self.expedition.reference} - {self.get_type_display()}"

    @property
    def extension(self):
        """Retourne l'extension du fichier."""
        return self.nom_original.split('.')[-1].lower() if '.' in self.nom_original else ''

    @property
    def is_image(self):
        """Vérifie si le document est une image."""
        return self.extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']

    @property
    def is_pdf(self):
        """Vérifie si le document est un PDF."""
        return self.extension == 'pdf'


class ClassificationChat(models.Model):
    """
    Session de chat pour la classification TARIC d'une expedition.
    Chaque expedition a une seule session de chat de classification.
    """
    expedition = models.OneToOneField(
        Expedition,
        on_delete=models.CASCADE,
        related_name='classification_chat',
        verbose_name="Expedition"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Cree le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifie le")

    class Meta:
        verbose_name = "Chat de classification"
        verbose_name_plural = "Chats de classification"

    def __str__(self):
        return f"Chat Classification - {self.expedition.reference}"

    def get_messages(self):
        """Retourne tous les messages ordonnes."""
        return self.messages.all().order_by('created_at')

    def get_latest_proposals(self):
        """Retourne les dernieres propositions TARIC."""
        latest_msg_with_proposals = self.messages.filter(
            proposals__isnull=False
        ).order_by('-created_at').first()
        if latest_msg_with_proposals:
            return latest_msg_with_proposals.proposals.all()
        return None

    def get_selected_proposal(self):
        """Retourne la proposition selectionnee si elle existe."""
        return TARICProposal.objects.filter(
            message__chat=self,
            is_selected=True
        ).first()


class ClassificationMessage(models.Model):
    """
    Message dans le chat de classification.
    """
    ROLE_CHOICES = [
        ('user', 'Utilisateur'),
        ('assistant', 'Assistant'),
        ('system', 'Systeme'),
    ]

    chat = models.ForeignKey(
        ClassificationChat,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Chat"
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name="Role"
    )
    content = models.TextField(verbose_name="Contenu")
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadonnees",
        help_text="Informations supplementaires (tools utilisees, tokens, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Cree le")

    class Meta:
        verbose_name = "Message de classification"
        verbose_name_plural = "Messages de classification"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}..."

    @property
    def has_proposals(self):
        """Verifie si ce message contient des propositions TARIC."""
        return self.proposals.exists()


class TARICProposal(models.Model):
    """
    Proposition de code TARIC generee par le chatbot.
    """
    message = models.ForeignKey(
        ClassificationMessage,
        on_delete=models.CASCADE,
        related_name='proposals',
        verbose_name="Message"
    )
    code_sh = models.CharField(
        max_length=6,
        verbose_name="Code SH (6 chiffres)"
    )
    code_nc = models.CharField(
        max_length=8,
        verbose_name="Code NC (8 chiffres)"
    )
    code_taric = models.CharField(
        max_length=10,
        verbose_name="Code TARIC (10 chiffres)"
    )
    probability = models.FloatField(
        verbose_name="Probabilite/Precision (%)"
    )
    description = models.CharField(
        max_length=255,
        verbose_name="Description"
    )
    justification = models.TextField(
        verbose_name="Justification"
    )
    ordre = models.IntegerField(
        default=0,
        verbose_name="Ordre d'affichage"
    )
    is_selected = models.BooleanField(
        default=False,
        verbose_name="Selectionne"
    )

    class Meta:
        verbose_name = "Proposition TARIC"
        verbose_name_plural = "Propositions TARIC"
        ordering = ['-probability']

    def __str__(self):
        return f"{self.code_taric} ({self.probability}%)"

    @property
    def formatted_code(self):
        """Retourne le code TARIC formate avec des points."""
        c = self.code_taric
        if len(c) == 10:
            return f"{c[:4]}.{c[4:6]}.{c[6:8]}.{c[8:]}"
        return c

    @property
    def confidence_level(self):
        """Retourne le niveau de confiance (high, medium, low)."""
        if self.probability >= 80:
            return 'high'
        elif self.probability >= 50:
            return 'medium'
        return 'low'

    @property
    def confidence_color(self):
        """Retourne la couleur Bootstrap selon le niveau de confiance."""
        levels = {
            'high': 'success',
            'medium': 'warning',
            'low': 'danger'
        }
        return levels.get(self.confidence_level, 'secondary')
