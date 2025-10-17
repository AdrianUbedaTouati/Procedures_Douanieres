from django.urls import path
from . import views

app_name = 'tenders'

urlpatterns = [
    # Dashboard principal
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Listado y filtrado de licitaciones
    path('buscar/', views.TenderListView.as_view(), name='list'),
    path('recomendadas/', views.RecommendedTendersView.as_view(), name='recommended'),

    # Guardadas
    path('guardadas/', views.SavedTendersView.as_view(), name='saved'),

    # Descarga de licitaciones desde TED (debe estar ANTES de los paths con parámetros dinámicos)
    path('obtener/', views.DownloadTendersFormView.as_view(), name='download_tenders'),
    path('descargar-licitaciones/', views.DownloadTendersExecuteView.as_view(), name='download_tenders_execute'),
    path('cancelar-descarga/', views.CancelDownloadView.as_view(), name='cancel_download'),

    # Generación de recomendaciones
    path('generar-recomendaciones/', views.GenerateRecommendationsView.as_view(), name='generate_recommendations'),

    # Borrar XMLs
    path('delete-all-xmls/', views.DeleteAllXMLsView.as_view(), name='delete_all_xmls'),
    path('delete-xml/<str:ojs_notice_id>/', views.DeleteXMLView.as_view(), name='delete_xml'),

    # Vectorización y gestión de ChromaDB
    path('vectorizacion/', views.VectorizationDashboardView.as_view(), name='vectorization_dashboard'),
    path('vectorizacion/indexar/', views.IndexAllTendersView.as_view(), name='index_all_tenders'),
    path('vectorizacion/limpiar/', views.ClearVectorstoreView.as_view(), name='clear_vectorstore'),
    path('vectorizacion/estado/', views.VectorstoreStatusAPIView.as_view(), name='vectorstore_status'),

    # Detalle de licitación (debe estar AL FINAL porque captura cualquier string)
    path('<str:ojs_notice_id>/', views.TenderDetailView.as_view(), name='detail'),
    path('<str:ojs_notice_id>/guardar/', views.SaveTenderView.as_view(), name='save'),
    path('<str:ojs_notice_id>/actualizar-estado/', views.UpdateSavedTenderStatusView.as_view(), name='update_status'),
]
