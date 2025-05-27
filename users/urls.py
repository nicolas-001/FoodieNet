from django.urls import path
from . import views
from .views import editar_perfil

app_name = 'users'

urlpatterns = [
    path('perfil/', views.perfil, name='perfil'),
    path('editar_perfil/', editar_perfil, name='editar_perfil'),
]