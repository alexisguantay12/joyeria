from django.urls import path
from . import views

app_name = 'reportes_app'  # si usás namespaces

urlpatterns = [
    path('ventas-por-local/', views.reporte_ventas_por_local, name='reporte_ventas_local'),
]




