from django.db import models 
# Importando librerias con el SoftDeletion y Timestamps
from django_timestamps.softDeletion import SoftDeletionModel
from django_timestamps.timestamps import TimestampsModel

# Create your models here.
  
from django.utils import timezone

class BaseAbstractWithUser(SoftDeletionModel, TimestampsModel):
    """
    Clase abstracta para usar los modelos SoftDeletion y Timestamps.
    Incluye:
      - is_deleted (inicia en False).
      - user_made, user_updated, user_deleted para registro de usuario.
      - delete() sobreescrito para cambiar is_deleted a True.
    """
    is_deleted = models.BooleanField(default=False)

    user_made = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="hecho por",
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

    def delete(self, using=None, keep_parents=False, user=None):
        """
        En lugar de eliminar físicamente, marca el registro como eliminado.
        Si recibe un usuario, lo asigna a user_deleted.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user:
            self.user_deleted = user
        self.save()

    def __str__(self) -> str:
        return (
            f"Creado por: {self.user_made}, "
            f"Última actualización por: {self.user_updated}, "
            f"Eliminado por: {self.user_deleted}"
        )
