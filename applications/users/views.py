# configuracion/views.py

from django.shortcuts import render, redirect
from applications.users.forms import CrearUsuarioForm
from applications.users.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.forms import AuthenticationForm


from django.contrib.auth.decorators import login_required

@login_required
def crear_usuario(request):
    if request.method == 'POST':
        form = CrearUsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('users_app:lista_usuarios')
    else:
        form = CrearUsuarioForm()
    return render(request, 'users/crear_usuario.html', {'form': form})

@login_required
def lista_usuarios(request):
    usuarios = User.objects.all()
    return render(request, 'users/lista_usuarios.html', {'usuarios': usuarios})

 

 
def login_view(request):
    if request.user.is_authenticated:
        return redirect('core_app:home')

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next')
            return redirect(next_url if next_url else 'core_app:home')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'users/login.html', {'form': form})
 
def logout_view(request):
    logout(request)
    return redirect('users_app:login')