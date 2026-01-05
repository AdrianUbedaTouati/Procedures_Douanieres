from django.contrib import admin
from .models import (
    Expedition, ExpeditionEtape, ExpeditionDocument,
    ClassificationData, DocumentsData, TransmissionData, PaiementData, OEAData
)


class ExpeditionEtapeInline(admin.TabularInline):
    model = ExpeditionEtape
    extra = 0
    readonly_fields = ['numero', 'type_etape', 'completed_at']
    fields = ['numero', 'type_etape', 'statut', 'completed_at']


class ExpeditionDocumentInline(admin.TabularInline):
    """Inline pour les documents d'une étape."""
    model = ExpeditionDocument
    extra = 0
    readonly_fields = ['created_at']
    fields = ['type', 'fichier', 'nom_original', 'created_at']


@admin.register(Expedition)
class ExpeditionAdmin(admin.ModelAdmin):
    list_display = ['reference', 'nom_article', 'user', 'direction', 'statut', 'etape_courante', 'created_at']
    list_filter = ['statut', 'direction', 'etape_courante', 'created_at']
    search_fields = ['reference', 'nom_article', 'description', 'user__email']
    readonly_fields = ['reference', 'created_at', 'updated_at']
    inlines = [ExpeditionEtapeInline]

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
    list_display = ['expedition', 'numero', 'type_etape', 'statut', 'completed_at']
    list_filter = ['numero', 'type_etape', 'statut']
    search_fields = ['expedition__reference', 'expedition__nom_article']
    readonly_fields = ['completed_at', 'created_at', 'updated_at']
    inlines = [ExpeditionDocumentInline]


@admin.register(ExpeditionDocument)
class ExpeditionDocumentAdmin(admin.ModelAdmin):
    list_display = ['get_expedition', 'type', 'nom_original', 'etape', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['etape__expedition__reference', 'nom_original']
    readonly_fields = ['created_at']

    def get_expedition(self, obj):
        return obj.etape.expedition.reference
    get_expedition.short_description = 'Expédition'


@admin.register(ClassificationData)
class ClassificationDataAdmin(admin.ModelAdmin):
    list_display = ['get_expedition', 'code_sh', 'code_nc', 'code_taric', 'proposition_selectionnee']
    search_fields = ['etape__expedition__reference', 'code_sh', 'code_nc', 'code_taric']
    readonly_fields = ['chat_historique', 'propositions']

    def get_expedition(self, obj):
        return obj.etape.expedition.reference
    get_expedition.short_description = 'Expédition'


@admin.register(DocumentsData)
class DocumentsDataAdmin(admin.ModelAdmin):
    list_display = ['get_expedition', 'dau_genere', 'd10_genere', 'd12_genere']

    def get_expedition(self, obj):
        return obj.etape.expedition.reference
    get_expedition.short_description = 'Expédition'


@admin.register(TransmissionData)
class TransmissionDataAdmin(admin.ModelAdmin):
    list_display = ['get_expedition', 'systeme_cible', 'reference_transmission', 'date_transmission']

    def get_expedition(self, obj):
        return obj.etape.expedition.reference
    get_expedition.short_description = 'Expédition'


@admin.register(PaiementData)
class PaiementDataAdmin(admin.ModelAdmin):
    list_display = ['get_expedition', 'montant_droits', 'montant_tva', 'date_paiement']

    def get_expedition(self, obj):
        return obj.etape.expedition.reference
    get_expedition.short_description = 'Expédition'


@admin.register(OEAData)
class OEADataAdmin(admin.ModelAdmin):
    list_display = ['get_expedition', 'statut_oea', 'numero_certificat']

    def get_expedition(self, obj):
        return obj.etape.expedition.reference
    get_expedition.short_description = 'Expédition'
