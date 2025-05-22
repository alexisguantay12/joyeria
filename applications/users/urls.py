# configuracion/urls.py

from django.urls import path
from . import views

app_name = 'users_app'

urlpatterns = [
    path('', views.lista_usuarios, name='lista_usuarios'),
    path('nuevo/', views.crear_usuario, name='crear_usuario'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
