# notifications/context_processors.py
from .models import Notificacion

def notificaciones_context(request):
    if request.user.is_authenticated:
        notificaciones = Notificacion.objects.filter(usuario=request.user)[:5]
        total = Notificacion.objects.filter(usuario=request.user, leida=False).count()
        return {'notificaciones': notificaciones, 'notificaciones_total': total}
    return {}
