"""
URLs pour l'étape de Paiement des Droits.
"""

from django.urls import path
from . import views

app_name = 'paiement'

urlpatterns = [
    path('', views.PaiementView.as_view(), name='index'),
]
