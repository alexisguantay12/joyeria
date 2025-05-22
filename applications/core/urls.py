from django.urls import path
from . import views

app_name = 'core_app'

urlpatterns = [
    path('', views.home_view, name='home'),  # Formulario para agregar producto
]
