from django import template

register = template.Library()

@register.filter
def split(value, key):
    if not value:
        return []
    # Se eliminan elementos vacíos y se quitan espacios
    return [x.strip() for x in value.split(key) if x.strip()]