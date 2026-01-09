"""
URLs pour l'etape de Generation des Documents.
"""

from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # Main view
    path('', views.DocumentsView.as_view(), name='index'),

    # Form for data entry
    path('form/', views.DocumentsFormView.as_view(), name='form'),

    # Preview before generation
    path('preview/<str:doc_type>/', views.DocumentsPreviewView.as_view(), name='preview'),

    # Generate document (API)
    path('generate/<str:doc_type>/', views.GenerateDocumentView.as_view(), name='generate'),

    # Download document
    path('download/<int:doc_id>/', views.DownloadDocumentView.as_view(), name='download'),

    # View document in browser
    path('view/<int:doc_id>/', views.ViewDocumentView.as_view(), name='view'),

    # Delete document
    path('delete/<int:doc_id>/', views.DeleteDocumentView.as_view(), name='delete'),

    # Validate stage
    path('validate/', views.ValidateDocumentsView.as_view(), name='validate'),
]
