"""
URLs pour l'étape de Gestion OEA.
"""

from django.urls import path
from . import views

app_name = 'oea'

urlpatterns = [
    path('', views.OeaView.as_view(), name='index'),
]
