from django.contrib import admin
from .models import Tender, SavedTender, TenderRecommendation


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ['ojs_notice_id', 'title', 'buyer_name', 'budget_amount', 'deadline', 'publication_date', 'contract_type', 'views_count']
    list_filter = ['contract_type', 'procedure_type', 'publication_date', 'deadline']
    search_fields = ['ojs_notice_id', 'title', 'buyer_name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'indexed_at', 'views_count']
    date_hierarchy = 'publication_date'

    fieldsets = (
        ('Identificación', {
            'fields': ('ojs_notice_id', 'title', 'description', 'short_description')
        }),
        ('Financiero', {
            'fields': ('budget_amount', 'currency')
        }),
        ('Clasificación', {
            'fields': ('cpv_codes', 'nuts_regions', 'contract_type')
        }),
        ('Comprador', {
            'fields': ('buyer_name', 'buyer_type')
        }),
        ('Fechas', {
            'fields': ('publication_date', 'deadline', 'tender_deadline_date', 'tender_deadline_time')
        }),
        ('Procedimiento', {
            'fields': ('procedure_type', 'award_criteria')
        }),
        ('Contacto', {
            'fields': ('contact_email', 'contact_phone', 'contact_url')
        }),
        ('Datos originales', {
            'fields': ('xml_content', 'source_path', 'xpaths_used'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('indexed_at', 'views_count', 'created_at', 'updated_at')
        }),
    )


@admin.register(SavedTender)
class SavedTenderAdmin(admin.ModelAdmin):
    list_display = ['user', 'tender', 'status', 'reminder_date', 'saved_at']
    list_filter = ['status', 'saved_at']
    search_fields = ['user__email', 'tender__ojs_notice_id', 'tender__title', 'notes']
    readonly_fields = ['saved_at']
    date_hierarchy = 'saved_at'

    fieldsets = (
        ('Relaciones', {
            'fields': ('user', 'tender')
        }),
        ('Estado y notas', {
            'fields': ('status', 'notes', 'reminder_date')
        }),
        ('Metadatos', {
            'fields': ('saved_at',)
        }),
    )


@admin.register(TenderRecommendation)
class TenderRecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'tender', 'recommendation_level', 'score_total', 'probability_success', 'generated_at']
    list_filter = ['recommendation_level', 'generated_at']
    search_fields = ['user__email', 'tender__ojs_notice_id', 'tender__title']
    readonly_fields = ['generated_at']
    date_hierarchy = 'generated_at'

    fieldsets = (
        ('Relaciones', {
            'fields': ('user', 'tender')
        }),
        ('Puntuaciones', {
            'fields': ('score_total', 'score_technical', 'score_budget', 'score_geographic', 'score_experience', 'score_competition')
        }),
        ('Análisis', {
            'fields': ('probability_success', 'recommendation_level', 'match_reasons', 'warning_factors')
        }),
        ('Información de contacto', {
            'fields': ('contact_info',)
        }),
        ('Metadatos', {
            'fields': ('generated_at',)
        }),
    )
