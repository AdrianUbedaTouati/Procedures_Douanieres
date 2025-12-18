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
    # Gestion des documents
    path('document/<int:doc_id>/supprimer/', views.DocumentDeleteView.as_view(), name='document_delete'),
    path('document/<int:doc_id>/renommer/', views.DocumentRenameView.as_view(), name='document_rename'),
    path('documents/reordonner/', views.DocumentReorderView.as_view(), name='documents_reorder'),
    # API Chat Classification
    path('chat/', views.ClassificationChatView.as_view(), name='chat'),
    path('chat/message/', views.ClassificationChatMessageView.as_view(), name='chat_message'),
    path('chat/proposal/<int:proposal_id>/select/', views.SelectTARICProposalView.as_view(), name='select_proposal'),
    path('chat/validate/', views.ValidateTARICCodeView.as_view(), name='validate_taric'),
]
