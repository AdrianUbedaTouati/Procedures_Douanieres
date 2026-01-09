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

    # Droits et taxes
    droits_douane = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Droits de douane",
        help_text="Taux de droits de douane (ex: 0%, 2.7%, Variable selon origine)"
    )
    tva = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        default="20%",
        verbose_name="TVA",
        help_text="Taux de TVA applicable"
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

    def add_message(self, role: str, content: str, metadata: dict = None):
        """Ajoute un message a l'historique du chat."""
        message = {
            'role': role,
            'content': content,
            'timestamp': timezone.now().isoformat()
        }
        if metadata:
            message['metadata'] = metadata
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
            self.droits_douane = proposal.get('droits_douane', '-')[:50] if proposal.get('droits_douane') else '-'
            self.tva = proposal.get('tva', '20%')[:20] if proposal.get('tva') else '20%'
            self.save(update_fields=['code_sh', 'code_nc', 'code_taric', 'droits_douane', 'tva'])
            return True
        return False


# =============================================================================
# DONNEES SPECIFIQUES: ETAPE 2 - DOCUMENTS
# =============================================================================

class DocumentsData(models.Model):
    """
    Donnees specifiques a l'etape 2: Generation de Documents.
    Stocke les donnees specifiques a chaque expedition pour la generation des documents DAU/D10/D12.
    """

    INCOTERMS_CHOICES = [
        ('EXW', 'EXW - Ex Works'),
        ('FCA', 'FCA - Free Carrier'),
        ('CPT', 'CPT - Carriage Paid To'),
        ('CIP', 'CIP - Carriage Insurance Paid'),
        ('DAP', 'DAP - Delivered At Place'),
        ('DPU', 'DPU - Delivered at Place Unloaded'),
        ('DDP', 'DDP - Delivered Duty Paid'),
        ('FAS', 'FAS - Free Alongside Ship'),
        ('FOB', 'FOB - Free On Board'),
        ('CFR', 'CFR - Cost and Freight'),
        ('CIF', 'CIF - Cost Insurance Freight'),
    ]

    CURRENCY_CHOICES = [
        ('EUR', 'Euro (EUR)'),
        ('DZD', 'Dinar algerien (DZD)'),
        ('USD', 'Dollar americain (USD)'),
    ]

    UNIT_CHOICES = [
        ('PCE', 'Pieces (PCE)'),
        ('KGM', 'Kilogrammes (KGM)'),
        ('MTR', 'Metres (MTR)'),
        ('LTR', 'Litres (LTR)'),
        ('MTQ', 'Metres cubes (MTQ)'),
        ('CTN', 'Cartons (CTN)'),
        ('PAL', 'Palettes (PAL)'),
    ]

    TRANSPORT_MODE_CHOICES = [
        ('sea', 'Maritime'),
        ('air', 'Aerien'),
        ('road', 'Routier'),
        ('rail', 'Ferroviaire'),
        ('multimodal', 'Multimodal'),
    ]

    TRANSPORT_DOC_CHOICES = [
        ('BL', 'Bill of Lading (B/L)'),
        ('AWB', 'Air Waybill (AWB)'),
        ('CMR', 'CMR (Route)'),
        ('CIM', 'CIM (Rail)'),
    ]

    etape = models.OneToOneField(
        ExpeditionEtape,
        on_delete=models.CASCADE,
        related_name='documents_data',
        verbose_name="Etape"
    )

    # ================================================
    # GENERATION STATUS
    # ================================================
    dau_genere = models.BooleanField(default=False, verbose_name="DAU genere")
    d10_genere = models.BooleanField(default=False, verbose_name="D10 genere")
    d12_genere = models.BooleanField(default=False, verbose_name="D12 genere")

    # ================================================
    # CONSIGNEE/IMPORTER INFORMATION
    # ================================================
    consignee_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nom du destinataire",
        help_text="Nom ou raison sociale du destinataire/importateur"
    )
    consignee_address = models.TextField(
        blank=True,
        verbose_name="Adresse du destinataire"
    )
    consignee_city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ville du destinataire"
    )
    consignee_postal_code = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Code postal destinataire"
    )
    consignee_country = models.CharField(
        max_length=100,
        blank=True,
        default='Algerie',
        verbose_name="Pays du destinataire"
    )
    consignee_country_code = models.CharField(
        max_length=2,
        blank=True,
        default='DZ',
        verbose_name="Code pays destinataire (ISO)"
    )
    consignee_tax_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="ID fiscal destinataire",
        help_text="NIF ou EORI du destinataire"
    )
    consignee_contact_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Contact chez le destinataire"
    )
    consignee_phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Telephone destinataire"
    )
    consignee_email = models.EmailField(
        blank=True,
        verbose_name="Email destinataire"
    )

    # ================================================
    # INVOICE DETAILS
    # ================================================
    invoice_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Numero de facture"
    )
    invoice_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de facture"
    )
    invoice_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montant total facture"
    )
    invoice_currency = models.CharField(
        max_length=3,
        blank=True,
        default='EUR',
        choices=CURRENCY_CHOICES,
        verbose_name="Devise"
    )

    # ================================================
    # PRODUCT DETAILS
    # ================================================
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Quantite"
    )
    unit_of_measure = models.CharField(
        max_length=20,
        blank=True,
        default='PCE',
        choices=UNIT_CHOICES,
        verbose_name="Unite de mesure"
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Prix unitaire"
    )
    gross_weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Poids brut (kg)"
    )
    net_weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Poids net (kg)"
    )
    number_of_packages = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Nombre de colis"
    )
    package_type = models.CharField(
        max_length=50,
        blank=True,
        default='Carton',
        verbose_name="Type d'emballage",
        help_text="Ex: Carton, Palette, Caisse, Sac"
    )

    # ================================================
    # TRANSPORT DETAILS
    # ================================================
    transport_mode = models.CharField(
        max_length=20,
        blank=True,
        choices=TRANSPORT_MODE_CHOICES,
        verbose_name="Mode de transport"
    )
    transport_mode_code = models.CharField(
        max_length=1,
        blank=True,
        verbose_name="Code mode transport",
        help_text="1=Maritime, 2=Rail, 3=Route, 4=Air"
    )
    transport_document_type = models.CharField(
        max_length=30,
        blank=True,
        choices=TRANSPORT_DOC_CHOICES,
        verbose_name="Type de document transport"
    )
    transport_document_ref = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Reference document transport",
        help_text="Numero du B/L, AWB, CMR, etc."
    )
    transport_document_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date document transport"
    )
    vessel_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nom du navire/vol",
        help_text="Nom du navire ou numero de vol"
    )
    port_of_loading = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Port/aeroport de chargement"
    )
    port_of_discharge = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Port/aeroport de dechargement"
    )
    expected_arrival_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date d'arrivee prevue"
    )

    # ================================================
    # COMMERCIAL TERMS
    # ================================================
    incoterms = models.CharField(
        max_length=3,
        blank=True,
        default='CIF',
        choices=INCOTERMS_CHOICES,
        verbose_name="Incoterms"
    )
    incoterms_location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Lieu Incoterms",
        help_text="Ex: CIF Alger, FOB Marseille"
    )
    freight_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Cout du fret"
    )
    insurance_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Cout de l'assurance"
    )

    # ================================================
    # ORIGIN INFORMATION
    # ================================================
    country_of_origin = models.CharField(
        max_length=100,
        blank=True,
        default='France',
        verbose_name="Pays d'origine"
    )
    country_of_origin_code = models.CharField(
        max_length=2,
        blank=True,
        default='FR',
        verbose_name="Code pays origine (ISO)"
    )
    country_of_dispatch = models.CharField(
        max_length=100,
        blank=True,
        default='France',
        verbose_name="Pays d'expedition"
    )
    country_of_dispatch_code = models.CharField(
        max_length=2,
        blank=True,
        default='FR',
        verbose_name="Code pays expedition (ISO)"
    )

    # ================================================
    # CUSTOMS PROCEDURE
    # ================================================
    customs_procedure_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Code regime douanier",
        help_text="Ex: 10 00 (mise a la consommation)"
    )
    customs_procedure_description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Description regime"
    )

    # ================================================
    # CALCULATED VALUES
    # ================================================
    fob_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Valeur FOB"
    )
    cif_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Valeur CIF",
        help_text="FOB + Fret + Assurance"
    )
    statistical_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Valeur statistique"
    )

    # ================================================
    # METADATA
    # ================================================
    form_completed = models.BooleanField(
        default=False,
        verbose_name="Formulaire complete"
    )

    class Meta:
        verbose_name = "Donnees Documents"
        verbose_name_plural = "Donnees Documents"

    def __str__(self):
        return f"Documents - {self.etape.expedition.reference}"

    def calculate_cif_value(self):
        """Calcule la valeur CIF = FOB + Fret + Assurance."""
        from decimal import Decimal
        fob = self.fob_value or self.invoice_total or Decimal('0')
        freight = self.freight_cost or Decimal('0')
        insurance = self.insurance_cost or Decimal('0')
        self.cif_value = fob + freight + insurance
        return self.cif_value

    def get_transport_mode_code(self):
        """Retourne le code transport pour les formulaires douaniers."""
        codes = {
            'sea': '1',
            'rail': '2',
            'road': '3',
            'air': '4',
            'multimodal': '7',
        }
        code = codes.get(self.transport_mode, '')
        self.transport_mode_code = code
        return code

    def get_required_documents(self):
        """Retourne la liste des documents requis selon la direction."""
        direction = self.etape.expedition.direction
        if direction == 'FR_DZ':
            return ['dau']  # Export EU
        else:  # DZ_FR
            return ['d10', 'd12']  # Import Algerie

    def get_consignee_full_address(self):
        """Retourne l'adresse complete du destinataire formatee."""
        parts = [
            self.consignee_address,
            self.consignee_postal_code,
            self.consignee_city,
            self.consignee_country,
        ]
        return ', '.join(filter(None, parts))


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


# =============================================================================
# DOCUMENTS WEB (descargados por el agente IA)
# =============================================================================

def web_document_upload_path(instance, filename):
    """
    Genera el path de upload para documentos web descargados por el agente.
    Format: {exp_id}/etape_1_classification/web_documents/{filename}
    """
    exp_id = instance.etape.expedition_id
    return f'{exp_id}/etape_1_classification/web_documents/{filename}'


class WebDocument(models.Model):
    """
    Documento descargado de internet por el agente IA durante la clasificacion.
    Puede ser una ficha tecnica, datasheet, normativa, etc.
    """

    etape = models.ForeignKey(
        ExpeditionEtape,
        on_delete=models.CASCADE,
        related_name='web_documents',
        verbose_name="Etape"
    )
    url_origen = models.URLField(
        max_length=2000,
        verbose_name="URL de origen",
        help_text="URL desde donde se descargo el documento"
    )
    titulo = models.CharField(
        max_length=255,
        verbose_name="Titulo",
        help_text="Titulo o descripcion del documento"
    )
    fichier = models.FileField(
        upload_to=web_document_upload_path,
        verbose_name="Fichier"
    )
    nom_fichier = models.CharField(
        max_length=255,
        verbose_name="Nom du fichier",
        help_text="Nombre del archivo guardado"
    )
    razon_guardado = models.TextField(
        blank=True,
        verbose_name="Razon de guardado",
        help_text="Por que el agente considero util guardar este documento"
    )
    texto_extraido = models.TextField(
        blank=True,
        verbose_name="Texto extraido",
        help_text="Preview del texto extraido del PDF"
    )
    tamano_bytes = models.IntegerField(
        default=0,
        verbose_name="Tamano en bytes"
    )
    paginas = models.IntegerField(
        default=0,
        verbose_name="Numero de paginas"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Descargado el")

    class Meta:
        verbose_name = "Document web"
        verbose_name_plural = "Documents web"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.titulo[:50]} - {self.etape.expedition.reference}"

    @property
    def expedition(self):
        """Raccourci pour acceder a l'expedition."""
        return self.etape.expedition

    @property
    def tamano_legible(self):
        """Retorna el tamano en formato legible (KB/MB)."""
        if self.tamano_bytes < 1024:
            return f"{self.tamano_bytes} B"
        elif self.tamano_bytes < 1024 * 1024:
            return f"{self.tamano_bytes / 1024:.1f} KB"
        else:
            return f"{self.tamano_bytes / (1024 * 1024):.1f} MB"

    @property
    def dominio_origen(self):
        """Extrae el dominio de la URL de origen."""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(self.url_origen)
            return parsed.netloc
        except Exception:
            return "unknown"
