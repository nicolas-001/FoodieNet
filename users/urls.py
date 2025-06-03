from django.urls import path
from . import views
from .views import editar_perfil

app_name = 'users'

urlpatterns = [
    path('perfil/', views.perfil, name='perfil'),
    path('editar_perfil/', editar_perfil, name='editar_perfil'),
    path('perfil/favoritos/', views.favoritos, name='favoritos'),
    path('buscar/', views.buscar_usuarios, name='buscar_usuarios'),
    path('enviar/<int:user_id>/', views.enviar_solicitud, name='enviar_solicitud'),
    path('solicitudes/', views.solicitudes_recibidas, name='solicitudes_recibidas'),
    path('aceptar/<int:request_id>/', views.aceptar_solicitud, name='aceptar_solicitud'),
    path('rechazar/<int:request_id>/', views.rechazar_solicitud, name='rechazar_solicitud'),
    path('<str:username>/', views.perfil_usuario, name='perfil_usuario'),

]