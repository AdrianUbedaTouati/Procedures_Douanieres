from django.urls import path
from . import views

app_name = 'tenders'

urlpatterns = [
    # Dashboard principal
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Listado y filtrado de licitaciones
    path('buscar/', views.TenderListView.as_view(), name='list'),
    path('recomendadas/', views.RecommendedTendersView.as_view(), name='recommended'),

    # Detalle de licitación
    path('<str:ojs_notice_id>/', views.TenderDetailView.as_view(), name='detail'),

    # Guardadas
    path('guardadas/', views.SavedTendersView.as_view(), name='saved'),
    path('<str:ojs_notice_id>/guardar/', views.SaveTenderView.as_view(), name='save'),
    path('<str:ojs_notice_id>/actualizar-estado/', views.UpdateSavedTenderStatusView.as_view(), name='update_status'),

    # Generación de recomendaciones
    path('generar-recomendaciones/', views.GenerateRecommendationsView.as_view(), name='generate_recommendations'),
]
