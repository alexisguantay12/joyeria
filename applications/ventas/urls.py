from django.urls import path
from .views import listado_ventas_view,agregar_venta_view,registrar_venta_api, eliminar_venta_api,detalle_venta_view

app_name = 'ventas_app'

urlpatterns = [
    path('', listado_ventas_view, name='listado_ventas'),
    path('agregar-venta/', agregar_venta_view, name='agregar_venta'),
    path('registrar-venta/',registrar_venta_api,name = 'registrar_venta'),
    path('eliminar/<int:id>/', eliminar_venta_api, name='eliminar_venta'),
    path('detalle/<int:id>/', detalle_venta_view, name='detalle_venta'),

]
