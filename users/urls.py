from django.urls import path
from . import views
from .views import editar_perfil, dashboard

app_name = 'users'

urlpatterns = [
    path('perfil/', views.perfil, name='perfil'),
    path('editar_perfil/', editar_perfil, name='editar_perfil'),
    path('perfil/favoritos/', views.favoritos, name='favoritos'),
    path('buscar/', views.buscar_usuarios_y_recetas, name='buscar_usuarios_y_recetas'),
    path('solicitudes/', views.solicitudes_amistad, name='solicitudes_amistad'),
    path('aceptar/<int:amistad_id>/', views.aceptar_amistad, name='aceptar_amistad'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('rechazar/<int:amistad_id>/', views.rechazar_amistad, name='rechazar_amistad'),
    path('agregar/<str:username>/', views.enviar_solicitud, name='enviar_solicitud'),
    path('<str:username>/', views.perfil_usuario, name='perfil_usuario'),
    path('cancelar-solicitud/<str:username>/', views.cancelar_solicitud, name='cancelar_solicitud'),
    path('borrar-amigo/<str:username>/', views.borrar_amigo, name='borrar_amigo'),
    

]