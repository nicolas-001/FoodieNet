from django import template

register = template.Library()

@register.filter
def badge_class(es_publica):
    """
    Devuelve la clase Bootstrap para el badge según la visibilidad.
    """
    return 'bg-success' if es_publica else 'bg-secondary'

@register.filter
def badge_label(es_publica):
    """
    Devuelve el texto del badge según la visibilidad.
    """
    return 'Pública' if es_publica else 'Privada'
