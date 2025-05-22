 

from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse 
from django.db import models


class User(AbstractUser):
    local = models.ForeignKey(
        'productos.Local',  # o el nombre de tu modelo de locales
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Local asignado"
    )