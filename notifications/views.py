from django.shortcuts import render, redirect, get_object_or_404
from .models import Notificacion
from django.contrib.auth.decorators import login_required

@login_required
def ver_todas(request):
    notificaciones = Notificacion.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'notifications/todas.html', {'notificaciones': notificaciones})

@login_required
def marcar_notificacion_leida(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
    notificacion.leida = True
    notificacion.save()
    # Redirigir a donde quieras (ej: página de notificaciones)
    return redirect('notifications:ver_todas')
@login_required
def marcar_todas_leidas(request):
    request.user.notificaciones.filter(leida=False).update(leida=True)
    return redirect('notifications:ver_todas')