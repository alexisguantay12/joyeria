# config/middlewares.py

from django.shortcuts import redirect
from django.urls import reverse

class LocalSeleccionadoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ruta_actual = request.path
        rutas_excluidas = [
            reverse('users_app:seleccionar_local'),
            reverse('users_app:logout'),
            reverse('users_app:login'),
        ]

        if request.user.is_authenticated:
            if 'local_id' not in request.session and ruta_actual not in rutas_excluidas:
                return redirect('users_app:seleccionar_local')

        return self.get_response(request)
