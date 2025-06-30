from django import template

register = template.Library()

@register.filter
def is_in_group(user, group_name):
    """Retorna True si el usuario pertenece al grupo especificado."""
    return user.groups.filter(name=group_name).exists()
