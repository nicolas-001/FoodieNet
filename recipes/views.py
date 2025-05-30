# recipes/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import models
from django.views.generic import UpdateView
from .models import Receta, Like, Favorito
from .forms import RecetaForm
from django.db.models import F

def lista_recetas(request):
    """Muestra todas las recetas."""
    recetas = Receta.objects.select_related('autor__perfil').all()
    return render(request, 'recipes/lista_recetas.html', {
        'recetas': recetas
    })

def detalle_receta(request, pk):
    # 1) incrementa contador atómico
    Receta.objects.filter(pk=pk).update(visitas=F('visitas') + 1)

    # 2) recupera la instancia (con el nuevo valor en memoria)
    receta = get_object_or_404(
        Receta.objects
               .select_related('autor__perfil')
               .annotate(
                   total_likes=models.Count('likes'),
                   total_favs =models.Count('favoritos')
               ),
        pk=pk
    )

    liked = False
    favorited = False
    if request.user.is_authenticated:
        liked     = receta.likes.filter(user=request.user).exists()
        favorited = receta.favoritos.filter(user=request.user).exists()

    return render(request, 'recipes/detalle_receta.html', {
        'receta': receta,
        'liked': liked,
        'favorited': favorited,
    })

@login_required
def crear_receta(request):
    """Crear una receta nueva."""
    if request.method == 'POST':
        form = RecetaForm(request.POST, request.FILES)
        if form.is_valid():
            nueva = form.save(commit=False)
            nueva.autor = request.user
            nueva.save()
            return redirect('detalle_receta', pk=nueva.pk)
    else:
        form = RecetaForm()
    return render(request, 'recipes/crear_receta.html', {'form': form})

class EditarRecetaView(UpdateView):
    """Editar una receta existente."""
    model = Receta
    form_class = RecetaForm
    template_name = 'recipes/receta_form.html'

    def get_success_url(self):
        return redirect('detalle_receta', pk=self.object.pk).url

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.autor != request.user:
            return redirect('detalle_receta', pk=obj.pk)
        return super().dispatch(request, *args, **kwargs)

@login_required
def borrar_receta(request, receta_id):
    """Borrar una receta (solo su autor)."""
    receta = get_object_or_404(Receta, id=receta_id, autor=request.user)
    receta.delete()
    return redirect('lista_recetas')

@login_required
def toggle_like(request, pk):
    """Dar o quitar like a una receta."""
    receta = get_object_or_404(Receta, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, receta=receta)
    if not created:
        like.delete()
    return redirect('detalle_receta', pk=pk)

@login_required
def toggle_favorito(request, pk):
    """Añadir o quitar una receta de favoritos."""
    receta = get_object_or_404(Receta, pk=pk)
    fav, created = Favorito.objects.get_or_create(user=request.user, receta=receta)
    if not created:
        fav.delete()
    return redirect('detalle_receta', pk=pk)
