"""
URLs pour l'étape de Transmission Électronique.
"""

from django.urls import path
from . import views

app_name = 'transmission'

urlpatterns = [
    path('', views.TransmissionView.as_view(), name='index'),
]
