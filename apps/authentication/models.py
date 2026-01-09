from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import uuid


class User(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)

    # Login attempts tracking
    login_attempts = models.IntegerField(default=0)
    last_login_attempt = models.DateTimeField(null=True, blank=True)
    login_blocked_until = models.DateTimeField(null=True, blank=True)

    # Profile fields
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # API Key for LLM (Google Gemini, OpenAI, NVIDIA, Ollama)
    llm_provider = models.CharField(
        max_length=20,
        choices=[
            ('gemini', 'Google Gemini'),
            ('openai', 'OpenAI'),
            ('nvidia', 'NVIDIA NIM'),
            ('ollama', 'Ollama (Local)'),
        ],
        default='gemini',
        verbose_name='Proveedor de IA',
        help_text='Selecciona tu proveedor de IA preferido'
    )
    llm_api_key = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='API Key',
        help_text='Tu API key del proveedor seleccionado (no necesaria para Ollama)'
    )

    # OpenAI specific fields
    openai_model = models.CharField(
        max_length=50,
        blank=True,
        default='gpt-4o-mini',
        choices=[
            ('gpt-4o', 'GPT-4o (Más potente, más caro)'),
            ('gpt-4o-mini', 'GPT-4o-mini (Balance calidad/precio)'),
            ('gpt-4-turbo', 'GPT-4 Turbo (Anterior generación)'),
            ('gpt-3.5-turbo', 'GPT-3.5 Turbo (Económico, menos capaz)'),
        ],
        verbose_name='Modelo OpenAI',
        help_text='Modelo de chat para OpenAI (gpt-4o-mini recomendado)'
    )
    openai_embedding_model = models.CharField(
        max_length=100,
        blank=True,
        default='text-embedding-3-small',
        choices=[
            ('text-embedding-3-small', 'text-embedding-3-small (Económico, recomendado)'),
            ('text-embedding-3-large', 'text-embedding-3-large (Más preciso, más caro)'),
            ('text-embedding-ada-002', 'text-embedding-ada-002 (Legacy)'),
        ],
        verbose_name='Modelo Embeddings OpenAI',
        help_text='Modelo de embeddings para OpenAI (text-embedding-3-small recomendado)'
    )

    # Ollama specific fields
    ollama_model = models.CharField(
        max_length=100,
        blank=True,
        default='qwen2.5:72b',
        verbose_name='Modelo Ollama',
        help_text='Modelo de chat para Ollama (ej: qwen2.5:72b, llama3.3:70b)'
    )
    ollama_embedding_model = models.CharField(
        max_length=100,
        blank=True,
        default='nomic-embed-text',
        verbose_name='Modelo Embeddings Ollama',
        help_text='Modelo de embeddings para Ollama (ej: nomic-embed-text, mxbai-embed-large)'
    )

    # Chat agent settings
    use_grading = models.BooleanField(
        default=False,
        verbose_name='Activar Grading',
        help_text='Activa el filtrado de documentos irrelevantes (más preciso pero más lento)'
    )
    use_verification = models.BooleanField(
        default=False,
        verbose_name='Activar Verificación XML',
        help_text='Valida campos críticos con el XML original (más preciso pero más lento)'
    )
    max_review_loops = models.IntegerField(
        default=3,
        verbose_name='Máximo de loops de revisión',
        help_text='Número máximo de veces que el sistema puede revisar y mejorar una respuesta (1-10). Default: 3. Más loops = mejor calidad pero más tiempo y tokens.'
    )

    # Google Search API settings
    use_web_search = models.BooleanField(
        default=False,
        verbose_name='Activar Búsqueda Web',
        help_text='Permite al agente buscar información actualizada en internet'
    )
    google_search_api_key = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Google Search API Key',
        help_text='API Key de Google Custom Search API'
    )
    google_search_engine_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Google Search Engine ID',
        help_text='ID del motor de búsqueda personalizado (cx parameter)'
    )
    browse_max_chars = models.IntegerField(
        default=10000,
        verbose_name='Máximo de caracteres por página',
        help_text='Número máximo de caracteres a extraer de cada página web (1,000 - 50,000). Más caracteres = más tokens = mayor costo pero más información detallada.'
    )
    browse_chunk_size = models.IntegerField(
        default=1250,
        verbose_name='Tamaño de fragmento de página',
        help_text='Número de caracteres por fragmento al analizar páginas (500 - browse_max_chars). Fragmentos más pequeños = más verificaciones pero mayor precisión. Aproximadamente 1 token = 4 caracteres.'
    )

    # Shipping address fields
    address_line1 = models.CharField(max_length=255, blank=True, verbose_name='Dirección (Línea 1)')
    address_line2 = models.CharField(max_length=255, blank=True, verbose_name='Dirección (Línea 2)')
    city = models.CharField(max_length=100, blank=True, verbose_name='Ciudad')
    state_province = models.CharField(max_length=100, blank=True, verbose_name='Estado/Provincia')
    postal_code = models.CharField(max_length=20, blank=True, verbose_name='Código Postal')
    country = models.CharField(max_length=100, blank=True, verbose_name='País', default='France')

    # ================================================
    # COMPANY INFORMATION (for customs documents)
    # ================================================
    company_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nom de l'entreprise",
        help_text="Raison sociale de l'entreprise"
    )
    company_legal_form = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Forme juridique",
        help_text="Ex: SARL, SAS, EURL, SA"
    )

    # ================================================
    # CUSTOMS IDENTIFIERS
    # ================================================
    eori_number = models.CharField(
        max_length=17,
        blank=True,
        verbose_name="Numero EORI",
        help_text="Economic Operator Registration and Identification (EU) - Ex: FR12345678901234"
    )
    nif_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="NIF",
        help_text="Numero d'Identification Fiscale (Algerie)"
    )
    vat_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Numero de TVA",
        help_text="Numero de TVA intracommunautaire - Ex: FR12345678901"
    )
    siret_number = models.CharField(
        max_length=14,
        blank=True,
        verbose_name="SIRET",
        help_text="Numero SIRET (France) - 14 chiffres"
    )

    # ================================================
    # CUSTOMS DEFAULTS
    # ================================================
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

    default_incoterms = models.CharField(
        max_length=3,
        blank=True,
        default='CIF',
        choices=INCOTERMS_CHOICES,
        verbose_name="Incoterms par defaut"
    )
    default_currency = models.CharField(
        max_length=3,
        blank=True,
        default='EUR',
        choices=CURRENCY_CHOICES,
        verbose_name="Devise par defaut"
    )

    # ================================================
    # CUSTOMS BROKER INFO (optional)
    # ================================================
    broker_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nom du transitaire",
        help_text="Nom du commissionnaire en douane"
    )
    broker_contact = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Contact transitaire",
        help_text="Telephone ou email du transitaire"
    )
    broker_customs_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Code agrement transitaire",
        help_text="Numero d'agrement douanier du transitaire"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def is_login_blocked(self):
        if self.login_blocked_until:
            if timezone.now() < self.login_blocked_until:
                return True
            else:
                self.login_blocked_until = None
                self.login_attempts = 0
                self.save()
        return False

    def increment_login_attempts(self):
        from django.conf import settings
        self.login_attempts += 1
        self.last_login_attempt = timezone.now()

        if settings.LOGIN_ATTEMPTS_ENABLED and self.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            self.login_blocked_until = timezone.now() + timezone.timedelta(
                minutes=settings.LOGIN_COOLDOWN_MINUTES
            )
        self.save()

    def reset_login_attempts(self):
        self.login_attempts = 0
        self.last_login_attempt = None
        self.login_blocked_until = None
        self.save()

    def generate_password_reset_token(self):
        return default_token_generator.make_token(self)

    def get_password_reset_uid(self):
        return urlsafe_base64_encode(force_bytes(self.pk))

    def get_full_address(self):
        """Devuelve la dirección completa formateada"""
        address_parts = []
        if self.address_line1:
            address_parts.append(self.address_line1)
        if self.address_line2:
            address_parts.append(self.address_line2)
        if self.city:
            address_parts.append(self.city)
        if self.state_province:
            address_parts.append(self.state_province)
        if self.postal_code:
            address_parts.append(self.postal_code)
        if self.country:
            address_parts.append(self.country)
        return ', '.join(address_parts) if address_parts else 'No especificada'

    def has_complete_address(self):
        """Verifica si el usuario tiene una dirección completa"""
        return all([self.address_line1, self.city, self.postal_code, self.country])

    def has_complete_customs_profile(self):
        """Verifie si le profil douanier est complet pour la generation de documents."""
        return all([
            self.company_name,
            self.address_line1,
            self.city,
            self.postal_code,
            self.country,
            self.eori_number or self.nif_number,  # At least one customs identifier
        ])

    def get_customs_identifier(self, direction='FR_DZ'):
        """Retourne l'identifiant douanier selon la direction."""
        if direction == 'FR_DZ':
            return self.eori_number
        else:  # DZ_FR
            return self.nif_number

    def get_company_full_info(self):
        """Retourne les informations completes de l'entreprise formatees."""
        parts = [self.company_name]
        if self.company_legal_form:
            parts[0] = f"{self.company_name} ({self.company_legal_form})"
        return parts[0] if parts else ''


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    def is_valid(self):
        # Token expires after 24 hours
        expiry_time = self.created_at + timezone.timedelta(hours=24)
        return not self.used and timezone.now() < expiry_time

    class Meta:
        ordering = ['-created_at']
