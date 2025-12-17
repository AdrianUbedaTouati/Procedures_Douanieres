"""
URLs pour l'étape de Classification Douanière.
"""

from django.urls import path
from . import views

app_name = 'classification'

urlpatterns = [
    path('', views.ClassificationView.as_view(), name='index'),
    path('upload/', views.ClassificationUploadView.as_view(), name='upload'),
    path('analyser/', views.ClassificationAnalyseView.as_view(), name='analyser'),
    path('valider/', views.ClassificationValiderView.as_view(), name='valider'),
]
