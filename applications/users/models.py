 

from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse 
from django.db import models


class User(AbstractUser):
    nombre = models.CharField(
        null=True,
        blank=True,
        max_length=100,
        verbose_name="Nombre"
    )