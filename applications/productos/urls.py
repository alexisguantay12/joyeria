from django.urls import path
from . import views

app_name = 'products_app'

urlpatterns = [
    path('agregar/', views.agregar_producto, name='agregar_producto'),  # Formulario para agregar producto
    path('', views.lista_productos, name='productos'),  # Listado de productos
    # urls.py
    path('producto/imprimir/<int:producto_id>/', views.imprimir_codigo, name='imprimir_codigo'),

    path('ingreso-mercaderia/', views.ingreso_mercaderia, name='ingreso_mercaderia'),
    path('buscar_producto_por_codigo/', views.buscar_producto_por_codigo, name='buscar_producto_por_codigo'),
    path('registrar_ingreso/', views.registrar_ingreso, name='registrar_ingreso'),
    path('producto/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
    path('ingresos/', views.lista_ingresos, name='lista_ingresos'),
    path('ingreso/<int:ingreso_id>/', views.detalle_ingreso, name='detalle_ingreso'),
]
