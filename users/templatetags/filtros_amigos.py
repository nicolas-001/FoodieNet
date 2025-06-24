from django import template

register = template.Library()

@register.filter
def es_amigo(user, otro):
    # Si user no está autenticado, devuelvo False para evitar errores
    if not user.is_authenticated:
        return False
    
    # Aquí pones la lógica original para comprobar amistad
    return Amistad.objects.filter(
        (Q(de_usuario=user) & Q(para_usuario=otro) & Q(aceptada=True)) |
        (Q(de_usuario=otro) & Q(para_usuario=user) & Q(aceptada=True))
    ).exists()