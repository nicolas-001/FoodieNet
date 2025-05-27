# recipes/urls.py
from django.urls import path
from . import views
from .views import crear_receta

urlpatterns = [
    path('recetas/', views.lista_recetas, name='lista_recetas'),
    path('recetas/<int:pk>/', views.detalle_receta, name='detalle_receta'),
    path('nueva/', crear_receta, name='crear_receta'),
    path('recetas/<int:pk>/editar/', views.EditarRecetaView.as_view(), name='editar_receta'), 
    path('borrar/<int:receta_id>/', views.borrar_receta, name='borrar_receta'),
]