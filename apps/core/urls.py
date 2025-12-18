from django.urls import path
from . import views

app_name = 'apps_core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    # Ollama verification
    path('ollama/check/', views.ollama_check_view, name='ollama_check'),
    path('ollama/test/', views.ollama_test_api, name='ollama_test'),
    path('ollama/models/', views.ollama_models_api, name='ollama_models'),
]