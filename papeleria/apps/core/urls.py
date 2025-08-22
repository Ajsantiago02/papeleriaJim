# apps/core/urls.py

from django.urls import path
from apps.core import views

app_name = 'core'

urlpatterns = [
    # URL del dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # URLs para productos
    path('productos/', views.ProductoListView.as_view(), name='producto-list'),
    path('productos/crear/', views.ProductoCreateView.as_view(), name='producto-create'),
    
    # URLs para categorías
    path('categorias/', views.CategoriaListView.as_view(), name='categoria-list'),
    path('categorias/crear/', views.CategoriaCreateView.as_view(), name='categoria-create'),

    #Venta
    path('venta/', views.VentaView.as_view(), name='nueva-venta'),
    path('upload-csv/', views.UploadCSVView.as_view(), name='upload_csv'),
    path('productos/editar/<int:pk>/', views.ProductoUpdateView.as_view(), name='producto-edit'),
    path('productos/<int:pk>/', views.producto_detail_json, name='producto-detail-json'),
    path('reportes/ventas/', views.ReportesVentaView.as_view(), name='reportes-ventas'),
    path('categorias/delete/<int:pk>/', views.CategoriaDeleteView.as_view(), name='categoria-delete'),
]