# configuracion/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
app_name = 'users_app'

urlpatterns = [
    path('', views.lista_usuarios, name='lista_usuarios'),
    path('nuevo/', views.crear_usuario, name='crear_usuario'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('cambiar-password/', auth_views.PasswordChangeView.as_view(
        template_name='users/cambiar_password.html',
        success_url='/usuarios/password-cambiado-ok/'
    ), name='cambiar_password'),
    
    path('password-cambiado-ok/', auth_views.PasswordChangeDoneView.as_view(
        template_name='users/password_cambiado_ok.html'
    ), name='password_cambiado_ok'),
]
