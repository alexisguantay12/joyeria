from django.urls import path
from . import views

app_name = 'reportes_app'  # si usás namespaces

urlpatterns = [
    path('ventas-por-local/', views.reporte_ventas_por_local, name='reporte_ventas_local'),
    path('stock-por-local/', views.reporte_stock_por_local, name='reporte_stock_local'),
]




