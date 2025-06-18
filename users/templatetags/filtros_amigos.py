from django import template
from users.models import Amistad
from django.db.models import Q


register = template.Library()

@register.filter
def es_amigo(usuario1, usuario2):
    if not usuario1 or not usuario2:
        return False
    return Amistad.objects.filter(
        (Q(de_usuario=usuario1) & Q(para_usuario=usuario2)) |
        (Q(de_usuario=usuario2) & Q(para_usuario=usuario1)),
        aceptada=True
    ).exists()
