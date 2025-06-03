from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from recipes.models import Receta, Favorito  # Ajusta si tu modelo se llama distinto
from .forms import UserEditForm,PerfilForm  # Formulario para editar usuario


@login_required
def perfil(request):
    """
    Muestra el perfil propio y, debajo, el formulario de edición.
    También muestra la lista de recetas favoritas.
    """
    usuario = request.user
    perfil = usuario.perfil  # Asegurarse de que el Perfil existe (se crea en signals)

    # Si vinimos por POST, procesamos los formularios
    if request.method == 'POST':
        form_user   = UserEditForm(request.POST, instance=usuario)
        form_perfil = PerfilForm(request.POST, request.FILES, instance=perfil)

        if form_user.is_valid() and form_perfil.is_valid():
            form_user.save()
            form_perfil.save()
            return redirect('users:perfil')
    else:
        form_user   = UserEditForm(instance=usuario)
        form_perfil = PerfilForm(instance=perfil)

    # Consultamos los favoritos para este usuario (asumiendo related_name='favoritos')
    favoritos = Favorito.objects.filter(user=usuario) \
                  .select_related('receta__autor__perfil')

    return render(
        request,
        'users/perfil.html',
        {
            'form_user': form_user,
            'form_perfil': form_perfil,
            'favoritos': favoritos,
        }
    )
@login_required
def editar_perfil(request):
    """
    Muestra un formulario propio donde el usuario puede editar
    su Username, Email, Foto y Biografía. Si el POST es válido,
    guarda y redirige de vuelta a /users/perfil/.
    """
    usuario = request.user
    perfil = usuario.perfil  # El OneToOne siempre debe existir gracias a signals

    if request.method == 'POST':
        form_user   = UserEditForm(request.POST, instance=usuario)
        form_perfil = PerfilForm(request.POST, request.FILES, instance=perfil)

        if form_user.is_valid() and form_perfil.is_valid():
            form_user.save()
            form_perfil.save()
            return redirect('users:perfil')
    else:
        form_user   = UserEditForm(instance=usuario)
        form_perfil = PerfilForm(instance=perfil)

    return render(request, 'users/editar_perfil.html', {
        'form_user': form_user,
        'form_perfil': form_perfil
    })
@login_required
def favoritos(request):
    """Lista las recetas que el usuario ha marcado como favoritas."""
    # Traemos todos los Favorito del usuario y precargamos la receta y su autor/perfil
    favoritos_qs = Favorito.objects.filter(user=request.user) \
                      .select_related('receta__autor__perfil')
    # Extraemos las recetas
    recetas_fav = [fav.receta for fav in favoritos_qs]

    return render(request, 'users/favoritos.html', {
        'recetas_fav': recetas_fav
    })

# users/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Perfil, FriendRequest
from .forms import UserSearchForm

@login_required
def buscar_usuarios(request):
    """
    Permite buscar usuarios por parte del username. Muestra resultados excluyendo:
    - el propio usuario
    - usuarios con los que ya se es amigo
    - a quienes ya se les ha enviado una solicitud pendiente
    """
    form = UserSearchForm(request.GET or None)
    resultados = []
    if form.is_valid():
        q = form.cleaned_data['query']
        # Filtrar: que contenga q, sin mayúsc/minusc y excluyendo:
        #   1) el propio usuario
        #   2) ya amigos (perfiles)
        #   3) solicitudes pendientes salientes
        #   4) solicitudes pendientes entrantes (opcional)
        usuario = request.user
        perfil = usuario.perfil

        # Usuarios ya amigos
        amigos_ids = perfil.amigos.values_list('user__id', flat=True)

        # Solicitudes enviadas
        enviados_ids = FriendRequest.objects.filter(from_user=usuario).values_list('to_user', flat=True)
        recibidos_ids = FriendRequest.objects.filter(to_user=usuario).values_list('from_user', flat=True)

        resultados = User.objects.filter(username__icontains=q).exclude(
            Q(id=usuario.id) |
            Q(id__in=amigos_ids) |
            Q(id__in=enviados_ids) |
            Q(id__in=recibidos_ids)
        )
    return render(request, 'users/buscar_usuarios.html', {
        'form': form,
        'resultados': resultados
    })


@login_required
def enviar_solicitud(request, user_id):
    """Envia una solicitud de amistad a otro usuario."""
    to_user = get_object_or_404(User, id=user_id)
    FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user)
    return redirect('users:buscar_usuarios')


@login_required
def solicitudes_recibidas(request):
    """Lista las solicitudes de amistad que me han enviado."""
    user = request.user
    solicitudes = FriendRequest.objects.filter(to_user=user)
    return render(request, 'users/solicitudes_recibidas.html', {
        'solicitudes': solicitudes
    })


@login_required
def aceptar_solicitud(request, request_id):
    """Acepta una solicitud: se agregan mutuamente a la lista de amigos."""
    fr = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    from_perfil = fr.from_user.perfil
    to_perfil   = request.user.perfil

    # Se agregan como amigos entre sí
    from_perfil.amigos.add(to_perfil)
    to_perfil.amigos.add(from_perfil)

    # Luego borramos la solicitud
    fr.delete()
    return redirect('users:solicitudes_recibidas')


@login_required
def rechazar_solicitud(request, request_id):
    """Rechaza (elimina) una solicitud recibida."""
    fr = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    fr.delete()
    return redirect('users:solicitudes_recibidas')


def perfil_usuario(request, username):
    """
    Vista pública del perfil de otro usuario:
    - Si soy amigo, muestro perfil completo y todas sus recetas (incluyendo privadas).
    - Si no soy amigo, muestro perfil “privado” con info reducida y solo sus recetas públicas.
    """
    otro = get_object_or_404(User, username=username)
    perfil_otro = otro.perfil
    recetas_otro = otro.receta_set  # QuerySet de Receta del autor

    if request.user.is_authenticated:
        # Verificar si somos amigos
        if request.user.perfil.amigos.filter(pk=perfil_otro.pk).exists():
            # Somos amigos: mostrar TODO
            recetas = recetas_otro.all()
            template = 'users/perfil_amigo.html'
        else:
            # No somos amigos: solo públicas
            recetas = recetas_otro.filter(es_publica=True)
            template = 'users/perfil_privado.html'
    else:
        # Usuario anónimo: misma vista “privada”
        recetas = recetas_otro.filter(es_publica=True)
        template = 'users/perfil_privado.html'

    return render(request, template, {
        'otro': otro,
        'perfil_otro': perfil_otro,
        'recetas': recetas,
    })
