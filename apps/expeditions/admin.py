from django.contrib import admin
from .models import Expedition, ExpeditionEtape, ExpeditionDocument


class ExpeditionEtapeInline(admin.TabularInline):
    model = ExpeditionEtape
    extra = 0
    readonly_fields = ['numero', 'completed_at']
    fields = ['numero', 'statut', 'completed_at']


class ExpeditionDocumentInline(admin.TabularInline):
    model = ExpeditionDocument
    extra = 0
    readonly_fields = ['created_at']
    fields = ['type', 'fichier', 'nom_original', 'etape', 'created_at']


@admin.register(Expedition)
class ExpeditionAdmin(admin.ModelAdmin):
    list_display = ['reference', 'nom_article', 'user', 'direction', 'statut', 'etape_courante', 'created_at']
    list_filter = ['statut', 'direction', 'etape_courante', 'created_at']
    search_fields = ['reference', 'nom_article', 'description', 'user__email']
    readonly_fields = ['reference', 'created_at', 'updated_at']
    inlines = [ExpeditionEtapeInline, ExpeditionDocumentInline]

    fieldsets = (
        ('Informations générales', {
            'fields': ('reference', 'nom_article', 'description', 'user')
        }),
        ('Statut', {
            'fields': ('direction', 'statut', 'etape_courante')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ExpeditionEtape)
class ExpeditionEtapeAdmin(admin.ModelAdmin):
    list_display = ['expedition', 'numero', 'statut', 'completed_at']
    list_filter = ['numero', 'statut']
    search_fields = ['expedition__reference', 'expedition__nom_article']
    readonly_fields = ['completed_at', 'created_at', 'updated_at']


@admin.register(ExpeditionDocument)
class ExpeditionDocumentAdmin(admin.ModelAdmin):
    list_display = ['expedition', 'type', 'nom_original', 'etape', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['expedition__reference', 'nom_original']
    readonly_fields = ['created_at']
