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

    # =========================================================================
    # ÉTAPE 2: GÉNÉRATION DES DOCUMENTS
    # =========================================================================
    path('<int:pk>/documents/',
         documents_views.DocumentsView.as_view(),
         name='documents'),

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
