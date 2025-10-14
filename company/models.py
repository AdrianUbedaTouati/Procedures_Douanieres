from django.db import models
from django.conf import settings


class CompanyProfile(models.Model):
    """Perfil de empresa personalizado para recomendaciones"""

    SIZE_CHOICES = [
        ('pequeña', 'Pequeña (1-50 empleados)'),
        ('mediana', 'Mediana (51-250 empleados)'),
        ('grande', 'Grande (250+ empleados)'),
    ]

    CAPACITY_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('buena', 'Buena'),
        ('alta', 'Alta'),
    ]

    RISK_CHOICES = [
        ('bajo', 'Bajo'),
        ('medio', 'Medio'),
        ('alto', 'Alto'),
    ]

    # Relación OneToOne con User
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_profile'
    )

    # Company Info
    company_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sectors = models.JSONField(default=list)
    certifications = models.JSONField(default=list)
    size = models.CharField(max_length=20, choices=SIZE_CHOICES, default='mediana')
    annual_revenue_eur = models.IntegerField(null=True, blank=True)
    employees = models.IntegerField(null=True, blank=True)
    years_in_business = models.IntegerField(null=True, blank=True)
    geographic_presence = models.JSONField(default=list, help_text='NUTS regions')

    # Capabilities
    technical_areas = models.JSONField(default=list)
    programming_languages = models.JSONField(default=list)
    technologies = models.JSONField(default=list)
    certifications_technical = models.JSONField(default=list)

    # Experience
    relevant_projects = models.JSONField(default=list)
    public_sector_experience = models.BooleanField(default=False)
    previous_clients = models.JSONField(default=list)

    # Bidding Preferences
    preferred_cpv_codes = models.JSONField(default=list)
    preferred_contract_types = models.JSONField(default=list)
    budget_range = models.JSONField(
        default=dict,
        help_text='{"min_eur": 200000, "max_eur": 3000000}'
    )
    preferred_regions = models.JSONField(default=list)
    max_concurrent_bids = models.IntegerField(default=5)
    avoid_keywords = models.JSONField(default=list)

    # Competitive Analysis
    main_competitors = models.JSONField(default=list)
    competitive_advantages = models.JSONField(default=list)
    weaknesses = models.JSONField(default=list)

    # Risk Factors
    financial_capacity = models.CharField(max_length=20, choices=CAPACITY_CHOICES, default='media')
    team_availability = models.CharField(max_length=20, choices=CAPACITY_CHOICES, default='buena')
    overcommitment_risk = models.CharField(max_length=20, choices=RISK_CHOICES, default='bajo')

    # Metadata
    is_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Perfil de Empresa'
        verbose_name_plural = 'Perfiles de Empresas'

    def __str__(self):
        return f"{self.company_name} ({self.user.email})"

    def to_agent_format(self):
        """Convierte el perfil al formato esperado por el motor de recomendaciones"""
        return {
            "company_info": {
                "name": self.company_name,
                "description": self.description,
                "sectors": self.sectors,
                "certifications": self.certifications,
                "size": self.size,
                "annual_revenue_eur": self.annual_revenue_eur or 0,
                "employees": self.employees or 0,
                "years_in_business": self.years_in_business or 0,
                "geographic_presence": self.geographic_presence,
            },
            "capabilities": {
                "technical_areas": self.technical_areas,
                "programming_languages": self.programming_languages,
                "technologies": self.technologies,
                "certifications_technical": self.certifications_technical,
            },
            "experience": {
                "relevant_projects": self.relevant_projects,
                "public_sector_experience": self.public_sector_experience,
                "previous_clients": self.previous_clients,
            },
            "bidding_preferences": {
                "preferred_cpv_codes": self.preferred_cpv_codes,
                "preferred_contract_types": self.preferred_contract_types,
                "budget_range": self.budget_range or {"min_eur": 200000, "max_eur": 3000000},
                "preferred_regions": self.preferred_regions,
                "max_concurrent_bids": self.max_concurrent_bids,
                "avoid_keywords": self.avoid_keywords,
            },
            "competitive_analysis": {
                "main_competitors": self.main_competitors,
                "competitive_advantages": self.competitive_advantages,
                "weaknesses": self.weaknesses,
            },
            "risk_factors": {
                "financial_capacity": self.financial_capacity,
                "team_availability": self.team_availability,
                "overcommitment_risk": self.overcommitment_risk,
            }
        }
