# configuracion/forms.py

from django import forms
from .models import User
from django.contrib.auth.models import Group
from applications.productos.models import Local
 
class CrearUsuarioForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Contraseña'
    )
    rol = forms.ChoiceField(
        choices=[
            ('administrador', 'Administrador'),
            ('vendedor', 'Vendedor'),
            ('cargador', 'Cargador')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Rol'
    )
    local = forms.ModelChoiceField(
        queryset=Local.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Local'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'rol', 'local']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}),
        }
        labels = {
            'username': 'Usuario',
            'email': 'Correo electrónico',
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()

            # Asignar grupo
            group_name = self.cleaned_data['rol']
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)

            # Asociar local si es vendedor
            if group_name == 'vendedor' and self.cleaned_data['local']:
                user.local = self.cleaned_data['local']
                user.save()
        return user
