from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def crear_grupos(sender, **kwargs):
    admin_group, _ = Group.objects.get_or_create(name='Administrador')
    vendedor_group, _ = Group.objects.get_or_create(name='Vendedor')
    cargador_group, _ = Group.objects.get_or_create(name='Cargador')

    permisos_vendedor = ['view_producto', 'view_venta', 'add_venta']
    permisos_cargador = ['view_producto', 'add_producto']

    for codename in permisos_vendedor:
        try:
            permiso = Permission.objects.get(codename=codename)
            vendedor_group.permissions.add(permiso)
        except Permission.DoesNotExist:
            pass

    for codename in permisos_cargador:
        try:
            permiso = Permission.objects.get(codename=codename)
            cargador_group.permissions.add(permiso)
        except Permission.DoesNotExist:
            pass
