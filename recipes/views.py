# recipes/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import F, Count, Q
from django.contrib.auth.decorators import login_required
from django.views.generic import UpdateView

from .models import Receta, Like, Favorito, Comentario
from .forms import RecetaForm, ComentarioForm
from users.models import Amistad
from django.core.paginator import Paginator


def lista_recetas(request):
    usuario = request.user
    if usuario.is_authenticated:
        amigos = usuario.perfil.obtener_amigos()
        recetas_qs = Receta.objects.filter(
            Q(es_publica=True) | 
            Q(es_publica=False, autor__in=amigos)
        ).select_related('autor__perfil').distinct().order_by('-fecha_creacion')
    else:
        recetas_qs = Receta.objects.filter(es_publica=True).select_related('autor__perfil').order_by('-fecha_creacion')

    # Paginación: 10 recetas por página
    paginator = Paginator(recetas_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recipes/lista_recetas.html', {
        'page_obj': page_obj,
    })
def detalle_receta(request, pk):
    receta = get_object_or_404(Receta.objects.select_related('autor__perfil'), pk=pk)

    # Validaciones de privacidad omitidas para simplificar

    if request.method == 'POST':
        # Procesar comentario
        if not request.user.is_authenticated:
            return redirect(f"{request.build_absolute_uri('/auth/login/')}?next={request.path}")

        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.autor = request.user
            comentario.receta = receta
            comentario.save()
            return redirect('detalle_receta', pk=pk)  # Para evitar repost con F5
    else:
        form = ComentarioForm()

    Receta.objects.filter(pk=pk).update(visitas=F('visitas') + 1)

    receta = Receta.objects.select_related('autor__perfil') \
        .annotate(total_likes=Count('likes'), total_favs=Count('favoritos')) \
        .get(pk=pk)

    user = request.user
    liked = user.is_authenticated and receta.likes.filter(user=user).exists()
    favorited = user.is_authenticated and receta.favoritos.filter(user=user).exists()

    comentarios = receta.comentarios.select_related('autor').order_by('-creado')

    return render(request, 'recipes/detalle_receta.html', {
        'receta': receta,
        'liked': liked,
        'favorited': favorited,
        'form': form,
        'comentarios': comentarios,
    })

@login_required
def crear_receta(request):
    """
    Crear una receta nueva. Sólo usuarios autenticados.
    """
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
    """
    Editar una receta existente. Sólo el autor puede acceder.
    """
    model = Receta
    form_class = RecetaForm
    template_name = 'recipes/editar_receta.html'

    def get_success_url(self):
        return redirect('detalle_receta', pk=self.object.pk).url

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.autor != request.user:
            return redirect('detalle_receta', pk=obj.pk)
        return super().dispatch(request, *args, **kwargs)


@login_required
def borrar_receta(request, receta_id):
    """
    Borrar una receta (sólo su autor).
    """
    receta = get_object_or_404(Receta, id=receta_id, autor=request.user)
    receta.delete()
    return redirect('lista_recetas')


@login_required
def toggle_like(request, pk):
    """
    Dar o quitar like a una receta.
    """
    receta = get_object_or_404(Receta, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, receta=receta)
    if not created:
        like.delete()
    return redirect('detalle_receta', pk=pk)


@login_required
def toggle_favorito(request, pk):
    """
    Añadir o quitar una receta de favoritos.
    """
    receta = get_object_or_404(Receta, pk=pk)
    fav, created = Favorito.objects.get_or_create(user=request.user, receta=receta)
    if not created:
        fav.delete()
    return redirect('detalle_receta', pk=pk)

@login_required
def feed_amigos(request):
    if not request.user.is_authenticated:
        # Redirigir o mostrar mensaje si no está autenticado
        # Por ejemplo, redirigir al login:
        from django.shortcuts import redirect
        return redirect('login')

    # Obtener amistades aceptadas donde el usuario es de_usuario o para_usuario
    amistades = Amistad.objects.filter(
        Q(de_usuario=request.user) | Q(para_usuario=request.user),
        aceptada=True
    )

    amigos_ids = set()
    for amistad in amistades:
        if amistad.de_usuario != request.user:
            amigos_ids.add(amistad.de_usuario.id)
        if amistad.para_usuario != request.user:
            amigos_ids.add(amistad.para_usuario.id)

    # Obtener recetas de amigos: públicas o privadas (de esos amigos)
    recetas = Receta.objects.filter(
        autor__id__in=amigos_ids
    ).order_by('-fecha_creacion')

    # PAGINACIÓN: 10 recetas por página
    paginator = Paginator(recetas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recipes/feed_amigos.html', {'page_obj': page_obj})