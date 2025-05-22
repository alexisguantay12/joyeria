from django.db import models 
# Importando librerias con el SoftDeletion y Timestamps
from django_timestamps.softDeletion import SoftDeletionModel
from django_timestamps.timestamps import TimestampsModel

# Create your models here.

from django_timestamps.softDeletion import SoftDeletionManager

class BaseAbstractWithUser(SoftDeletionModel, TimestampsModel):
    """
    Clase Abstracta para usar los modelos SoftDeletion y Timesstamps

    incluira el created_at, updated_at, deleted_at y user_made
    """
    user_made = models.ForeignKey(
        'users.User', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        verbose_name="echo por",
        related_name="%(class)s_user_made"
    )

    user_updated = models.ForeignKey(
        'users.User', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        verbose_name="actualizado por",
        related_name="%(class)s_user_updated"
    )
    
    
    user_deleted = models.ForeignKey(
        'users.User', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        verbose_name="eliminado por",
        related_name="%(class)s_user_deleted"
    )


    class Meta:
        abstract = True


    def __str__(self) -> str:
        return f"Creado por: {self.user_made}, Última actualización por: {self.user_updated}, Eliminado por: {self.user_deleted}"
    
