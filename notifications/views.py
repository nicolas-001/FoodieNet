from django.shortcuts import render
from .models import Notificacion
from django.contrib.auth.decorators import login_required

@login_required
def ver_todas(request):
    notificaciones = Notificacion.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'notifications/todas.html', {'notificaciones': notificaciones})

