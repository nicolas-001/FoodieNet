from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('todas/', views.ver_todas, name='ver_todas'),
    path('marcar-leida/<int:pk>/', views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    path('marcar-todas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),


]
