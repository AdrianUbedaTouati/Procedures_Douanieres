"""
URLs pour le module Expéditions.
Structure modulaire avec sous-URLs par étape.
"""

from django.urls import path, include
from . import views

# Import des vues depuis les modules d'étapes
from .etapes.classification import views as classification_views
from .etapes.documents import views as documents_views
from .etapes.transmission import views as transmission_views
from .etapes.paiement import views as paiement_views
from .etapes.oea import views as oea_views

app_name = 'apps_expeditions'

urlpatterns = [
    # =========================================================================
    # GESTION DES EXPÉDITIONS
    # =========================================================================

    # Liste des expéditions
    path('', views.ExpeditionListView.as_view(), name='list'),

    # Créer nouvelle expédition
    path('nouvelle/', views.ExpeditionCreateView.as_view(), name='create'),

    # Détail d'une expédition (avec toutes les étapes)
    path('<int:pk>/', views.ExpeditionDetailView.as_view(), name='detail'),

    # Supprimer une expédition
    path('<int:pk>/supprimer/', views.ExpeditionDeleteView.as_view(), name='delete'),

    # Télécharger tous les documents d'une étape en ZIP
    path('<int:pk>/etape/<int:etape_numero>/download-zip/',
         views.DownloadDocumentsZipView.as_view(),
         name='download_documents_zip'),

    # =========================================================================
    # ÉTAPE 1: CLASSIFICATION DOUANIÈRE
    # =========================================================================
    path('<int:pk>/classification/',
         classification_views.ClassificationView.as_view(),
         name='classification'),
    path('<int:pk>/classification/upload/',
         classification_views.ClassificationUploadView.as_view(),
         name='classification_upload'),
    path('<int:pk>/classification/analyser/',
         classification_views.ClassificationAnalyseView.as_view(),
         name='classification_analyse'),
    path('<int:pk>/classification/valider/',
         classification_views.ClassificationValiderView.as_view(),
         name='classification_valider'),
    # Gestion des documents classification
    path('<int:pk>/classification/document/<int:doc_id>/supprimer/',
         classification_views.DocumentDeleteView.as_view(),
         name='classification_document_delete'),
    path('<int:pk>/classification/document/<int:doc_id>/renommer/',
         classification_views.DocumentRenameView.as_view(),
         name='classification_document_rename'),
    path('<int:pk>/classification/documents/reordonner/',
         classification_views.DocumentReorderView.as_view(),
         name='classification_documents_reorder'),
    # API Chat Classification TARIC
    path('<int:pk>/classification/chat/',
         classification_views.ClassificationChatView.as_view(),
         name='classification_chat'),
    path('<int:pk>/classification/chat/message/',
         classification_views.ClassificationChatMessageView.as_view(),
         name='classification_chat_message'),
    path('<int:pk>/classification/chat/analyze/',
         classification_views.ClassificationAnalyzeDocumentsView.as_view(),
         name='classification_chat_analyze'),
    path('<int:pk>/classification/chat/proposal/<int:proposal_id>/select/',
         classification_views.SelectTARICProposalView.as_view(),
         name='classification_select_proposal'),
    path('<int:pk>/classification/chat/validate/',
         classification_views.ValidateTARICCodeView.as_view(),
         name='classification_validate_taric'),
    # API Web Documents (descargados por IA)
    path('<int:pk>/classification/web-documents/',
         classification_views.WebDocumentsListView.as_view(),
         name='classification_web_documents'),

    # =========================================================================
    # ÉTAPE 2: GÉNÉRATION DES DOCUMENTS
    # =========================================================================
    path('<int:pk>/documents/',
         documents_views.DocumentsView.as_view(),
         name='documents'),
    path('<int:pk>/documents/form/',
         documents_views.DocumentsFormView.as_view(),
         name='documents_form'),
    path('<int:pk>/documents/preview/<str:doc_type>/',
         documents_views.DocumentsPreviewView.as_view(),
         name='documents_preview'),
    path('<int:pk>/documents/generate/<str:doc_type>/',
         documents_views.GenerateDocumentView.as_view(),
         name='documents_generate'),
    path('<int:pk>/documents/download/<int:doc_id>/',
         documents_views.DownloadDocumentView.as_view(),
         name='documents_download'),
    path('<int:pk>/documents/view/<int:doc_id>/',
         documents_views.ViewDocumentView.as_view(),
         name='documents_view'),
    path('<int:pk>/documents/delete/<int:doc_id>/',
         documents_views.DeleteDocumentView.as_view(),
         name='documents_delete'),
    path('<int:pk>/documents/validate/',
         documents_views.ValidateDocumentsView.as_view(),
         name='documents_validate'),
    # User profile update for documents
    path('update-profile/',
         documents_views.UpdateUserProfileView.as_view(),
         name='update_profile'),

    # =========================================================================
    # ÉTAPE 3: TRANSMISSION ÉLECTRONIQUE
    # =========================================================================
    path('<int:pk>/transmission/',
         transmission_views.TransmissionView.as_view(),
         name='transmission'),

    # =========================================================================
    # ÉTAPE 4: PAIEMENT DES DROITS
    # =========================================================================
    path('<int:pk>/paiement/',
         paiement_views.PaiementView.as_view(),
         name='paiement'),

    # =========================================================================
    # ÉTAPE 5: GESTION OEA
    # =========================================================================
    path('<int:pk>/oea/',
         oea_views.OeaView.as_view(),
         name='oea'),
]
