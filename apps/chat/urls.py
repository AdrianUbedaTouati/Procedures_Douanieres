from django.urls import path
from . import views

app_name = 'apps_chat'

urlpatterns = [
    # Lista de sesiones de chat
    path('', views.ChatSessionListView.as_view(), name='session_list'),

    # Crear nueva sesión
    path('nueva/', views.ChatSessionCreateView.as_view(), name='session_create'),

    # Vista de sesión específica
    path('<int:session_id>/', views.ChatSessionDetailView.as_view(), name='session_detail'),

    # Enviar mensaje
    path('<int:session_id>/mensaje/', views.ChatMessageCreateView.as_view(), name='message_create'),

    # Archivar sesión
    path('<int:session_id>/archivar/', views.ChatSessionArchiveView.as_view(), name='session_archive'),

    # Eliminar sesión
    path('<int:session_id>/eliminar/', views.ChatSessionDeleteView.as_view(), name='session_delete'),
]
