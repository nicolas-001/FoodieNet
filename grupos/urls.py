# recetas/urls.py
from django.urls import path
from . import views

app_name = "grupos"

urlpatterns = [
    path("", views.grupo_list, name="grupo_list"),
    path("<int:pk>/", views.grupo_detalle, name="grupo_detalle"),
    path("crear/", views.grupo_crear, name="grupo_crear"),
    path("<int:pk>/unirse/", views.grupo_unirse, name="grupo_unirse"),
    path("<int:pk>/salir/", views.grupo_salir, name="grupo_salir"),
    path("<int:pk>/editar/", views.grupo_editar, name="grupo_editar"), 
    path("<int:pk>/agregar-receta/", views.grupo_agregar_receta, name="grupo_agregar_receta"),
    path("explorar/", views.explorar_grupos, name="explorar_grupos"),
    path('<int:pk>/borrar/', views.grupo_borrar, name='grupo_borrar')

]

