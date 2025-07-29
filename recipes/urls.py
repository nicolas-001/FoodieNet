# recipes/urls.py
from django.urls import path
from . import views
from .views import crear_receta, feed_amigos

urlpatterns = [
    path('recetas/', views.lista_recetas, name='lista_recetas'),
    path('recetas/<int:pk>/', views.detalle_receta, name='detalle_receta'),
    path('nueva/', crear_receta, name='crear_receta'),
    ##path('recetas/<int:pk>/comentar/', views.comentar_receta, name='comentar_receta'),
    path('recetas/<int:pk>/editar/', views.EditarRecetaView.as_view(), name='editar_receta'), 
    path('borrar/<int:receta_id>/', views.borrar_receta, name='borrar_receta'),
    path('recetas/<int:pk>/like/',     views.toggle_like,      name='toggle_like'),
    path('recetas/<int:pk>/favorito/', views.toggle_favorito,  name='toggle_favorito'),
    path('feed_amigos/', feed_amigos, name='feed_amigos'),
    path('calcular_calorias/<int:receta_id>/', views.calcular_calorias_macros, name='calcular_calorias'),
    path('probar_recomendador/', views.probar_recomendador, name='probar_recomendador'),
    path('seleccionar_ingredientes/', views.seleccionar_ingredientes, name='seleccionar_ingredientes'),
]