from django.db import models
from django.conf import settings
from decimal import Decimal


class Tender(models.Model):
    """Modelo para licitaciones públicas"""

    CONTRACT_TYPE_CHOICES = [
        ('services', 'Servicios'),
        ('supplies', 'Suministros'),
        ('works', 'Obras'),
    ]

    PROCEDURE_TYPE_CHOICES = [
        ('open', 'Abierto'),
        ('restricted', 'Restringido'),
        ('negotiated', 'Negociado'),
        ('competitive_dialogue', 'Diálogo competitivo'),
    ]

    # Identificación
    ojs_notice_id = models.CharField(max_length=100, unique=True, verbose_name='ID Aviso OJS')
    title = models.CharField(max_length=500, verbose_name='Título')
    description = models.TextField(verbose_name='Descripción')
    short_description = models.CharField(max_length=500, blank=True, verbose_name='Descripción corta')

    # Financiero
    budget_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Presupuesto'
    )
    currency = models.CharField(max_length=3, default='EUR', verbose_name='Moneda')

    # Clasificación
    cpv_codes = models.JSONField(default=list, verbose_name='Códigos CPV')
    nuts_regions = models.JSONField(default=list, verbose_name='Regiones NUTS')
    contract_type = models.CharField(
        max_length=50,
        choices=CONTRACT_TYPE_CHOICES,
        default='services',
        verbose_name='Tipo de contrato'
    )

    # Comprador
    buyer_name = models.CharField(max_length=300, verbose_name='Organismo contratante')
    buyer_type = models.CharField(max_length=100, blank=True, verbose_name='Tipo de organismo')

    # Fechas límite
    publication_date = models.DateField(null=True, blank=True, verbose_name='Fecha de publicación')
    deadline = models.DateTimeField(null=True, blank=True, verbose_name='Fecha límite')
    tender_deadline_date = models.DateField(null=True, blank=True, verbose_name='Fecha límite de oferta')
    tender_deadline_time = models.TimeField(null=True, blank=True, verbose_name='Hora límite')

    # Procedimiento
    procedure_type = models.CharField(
        max_length=50,
        choices=PROCEDURE_TYPE_CHOICES,
        default='open',
        verbose_name='Tipo de procedimiento'
    )
    award_criteria = models.JSONField(default=dict, verbose_name='Criterios de adjudicación')

    # Contacto
    contact_email = models.EmailField(blank=True, verbose_name='Email de contacto')
    contact_phone = models.CharField(max_length=50, blank=True, verbose_name='Teléfono de contacto')
    contact_url = models.URLField(blank=True, verbose_name='URL de contacto')

    # Datos originales
    xml_content = models.TextField(blank=True, verbose_name='Contenido XML original')
    source_path = models.CharField(max_length=500, blank=True, verbose_name='Ruta del archivo XML')
    xpaths_used = models.JSONField(default=dict, verbose_name='XPaths utilizados')

    # Metadatos
    indexed_at = models.DateTimeField(null=True, blank=True, verbose_name='Indexado en')
    views_count = models.IntegerField(default=0, verbose_name='Vistas')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado en')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado en')

    class Meta:
        verbose_name = 'Licitación'
        verbose_name_plural = 'Licitaciones'
        ordering = ['-publication_date', '-created_at']
        indexes = [
            models.Index(fields=['ojs_notice_id']),
            models.Index(fields=['-publication_date']),
            models.Index(fields=['-deadline']),
        ]

    def __str__(self):
        return f"{self.ojs_notice_id} - {self.title[:50]}"

    def increment_views(self):
        """Incrementa el contador de vistas"""
        self.views_count += 1
        self.save(update_fields=['views_count'])

    @property
    def is_expired(self):
        """Verifica si la licitación ha expirado"""
        if self.deadline:
            from django.utils import timezone
            return timezone.now() > self.deadline
        return False


class SavedTender(models.Model):
    """Licitaciones guardadas por el usuario"""

    STATUS_CHOICES = [
        ('interested', 'Interesado'),
        ('applied', 'Oferta presentada'),
        ('won', 'Ganada'),
        ('lost', 'Perdida'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_tenders',
        verbose_name='Usuario'
    )
    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name='saved_by',
        verbose_name='Licitación'
    )
    notes = models.TextField(blank=True, verbose_name='Notas')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='interested',
        verbose_name='Estado'
    )
    reminder_date = models.DateTimeField(null=True, blank=True, verbose_name='Recordatorio')
    saved_at = models.DateTimeField(auto_now_add=True, verbose_name='Guardado en')

    class Meta:
        verbose_name = 'Licitación guardada'
        verbose_name_plural = 'Licitaciones guardadas'
        unique_together = ['user', 'tender']
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.email} - {self.tender.ojs_notice_id}"


class TenderRecommendation(models.Model):
    """Recomendaciones de licitaciones para usuarios"""

    RECOMMENDATION_LEVEL_CHOICES = [
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tender_recommendations',
        verbose_name='Usuario'
    )
    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name='recommendations',
        verbose_name='Licitación'
    )

    # Scores (0-100)
    score_total = models.FloatField(verbose_name='Score total')
    score_technical = models.FloatField(verbose_name='Score técnico')
    score_budget = models.FloatField(verbose_name='Score presupuesto')
    score_geographic = models.FloatField(verbose_name='Score geográfico')
    score_experience = models.FloatField(verbose_name='Score experiencia')
    score_competition = models.FloatField(verbose_name='Score competencia')

    # Probabilidad de éxito
    probability_success = models.FloatField(verbose_name='Probabilidad de éxito')

    # Razones y advertencias
    match_reasons = models.JSONField(default=list, verbose_name='Razones de compatibilidad')
    warning_factors = models.JSONField(default=list, verbose_name='Factores de advertencia')

    # Nivel de recomendación
    recommendation_level = models.CharField(
        max_length=10,
        choices=RECOMMENDATION_LEVEL_CHOICES,
        verbose_name='Nivel de recomendación'
    )

    # Información de contacto extraída
    contact_info = models.JSONField(default=dict, verbose_name='Información de contacto')

    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name='Generado en')

    class Meta:
        verbose_name = 'Recomendación de licitación'
        verbose_name_plural = 'Recomendaciones de licitaciones'
        unique_together = ['user', 'tender']
        ordering = ['-score_total', '-generated_at']
        indexes = [
            models.Index(fields=['user', '-score_total']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.tender.ojs_notice_id} ({self.score_total:.1f})"

    @property
    def score_breakdown(self):
        """Retorna el desglose de scores para gráficos"""
        return {
            'Técnico': self.score_technical,
            'Presupuesto': self.score_budget,
            'Geográfico': self.score_geographic,
            'Experiencia': self.score_experience,
            'Competencia': self.score_competition,
        }
