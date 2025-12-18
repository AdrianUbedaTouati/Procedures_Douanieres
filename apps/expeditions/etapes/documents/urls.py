"""
URLs pour l'étape de Génération des Documents.
"""

from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.DocumentsView.as_view(), name='index'),
]
