from django.urls import path
from . import views

app_name = 'company'

urlpatterns = [
    # Perfil de empresa (edición)
    path('perfil/', views.CompanyProfileView.as_view(), name='profile'),

    # Vista de solo lectura
    path('perfil/ver/', views.CompanyProfileDetailView.as_view(), name='profile_detail'),
]
