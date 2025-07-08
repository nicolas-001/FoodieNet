from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from recipes.models import Receta, Favorito  # Ajusta si tu modelo se llama distinto
from .forms import UserEditForm,PerfilForm  # Formulario para editar usuario
from .models import Amistad
from django.contrib import messages
from django.http import JsonResponse


@login_required
def perfil(request):
    """
    Muestra el perfil propio y, debajo, el formulario de edición.
    También muestra la lista de recetas favoritas y las recetas del usuario.
    """
    usuario = request.user
    perfil = usuario.perfil  # Asegurarse de que el Perfil existe (se crea en signals)

    if request.method == 'POST':
        form_user = UserEditForm(request.POST, instance=usuario)
        form_perfil = PerfilForm(request.POST, request.FILES, instance=perfil)

        if form_user.is_valid() and form_perfil.is_valid():
            form_user.save()
            form_perfil.save()
            return redirect('users:perfil')
    else:
        form_user = UserEditForm(instance=usuario)
        form_perfil = PerfilForm(instance=perfil)

    favoritos = Favorito.objects.filter(user=usuario).select_related('receta__autor__perfil')
    amigos = obtener_amigos(request.user)
    solicitudes_pendientes = Amistad.objects.filter(para_usuario=usuario, aceptada=False).select_related('de_usuario')
    
    # 👉 Aquí añadimos las recetas subidas por el usuario
    recetas = usuario.receta_set.all()

    return render(
        request,
        'users/perfil.html',
        {
            'form_user': form_user,
            'form_perfil': form_perfil,
            'favoritos': favoritos,
            'amigos': amigos,
            'solicitudes_pendientes': solicitudes_pendientes,
            'recetas': recetas,  # <-- Añadido al contexto
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
from django.core.paginator import Paginator

def buscar_usuarios(request):
    query = request.GET.get('query')
    resultados = User.objects.none()

    if query:
        resultados = User.objects.filter(username__icontains=query).order_by('username')

    # Paginación: 10 usuarios por página
    paginator = Paginator(resultados, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'users/buscar_usuarios.html', {
        'page_obj': page_obj,
        'query': query
    })


def perfil_usuario(request, username):
    otro = get_object_or_404(User, username=username)
    perfil_otro = otro.perfil
    recetas_otro = otro.receta_set.all()

    amigos = obtener_amigos(otro)  

    es_amigo = False
    solicitud_pendiente = False

    if request.user.is_authenticated:
        es_amigo = Amistad.objects.filter(
            (Q(de_usuario=request.user) & Q(para_usuario=otro) & Q(aceptada=True)) |
            (Q(de_usuario=otro) & Q(para_usuario=request.user) & Q(aceptada=True))
        ).exists()

        solicitud_pendiente = Amistad.objects.filter(
            (Q(de_usuario=request.user) & Q(para_usuario=otro) & Q(aceptada=False)) |
            (Q(de_usuario=otro) & Q(para_usuario=request.user) & Q(aceptada=False))
        ).exists()

    # Separamos las recetas según privacidad
    recetas_publicas = recetas_otro.filter(es_publica=True)
    recetas_privadas = recetas_otro.filter(es_publica=False)

    return render(request, 'users/perfil_usuario.html', {
        'otro': otro,
        'perfil_otro': perfil_otro,
        'recetas_publicas': recetas_publicas,
        'recetas_privadas': recetas_privadas,
        'amigos': amigos,
        'es_amigo': es_amigo,
        'solicitud_pendiente': solicitud_pendiente
    })

@login_required
def solicitudes_amistad(request):
    solicitudes = Amistad.objects.filter(para_usuario=request.user, aceptada=False)
    return render(request, 'users/solicitudes_amistad.html', {'solicitudes': solicitudes})

@login_required
def aceptar_amistad(request, amistad_id):
    if request.method == "POST":
        solicitud = get_object_or_404(Amistad, id=amistad_id, para_usuario=request.user, aceptada=False)
        solicitud.aceptada = True
        solicitud.save()

        # Obtener amigos aceptados
        amigos_qs = Amistad.objects.filter(
            Q(de_usuario=request.user) | Q(para_usuario=request.user),
            aceptada=True
        )

        amigos_list = []
        for amistad in amigos_qs:
            # Obtener el usuario amigo (el otro usuario en la relación)
            if amistad.de_usuario == request.user:
                amigo = amistad.para_usuario
            else:
                amigo = amistad.de_usuario

            amigos_list.append({
                'username': amigo.username,
                'perfil_foto_url': amigo.perfil.foto.url if amigo.perfil.foto else '/static/perfiles/default.jpeg'
            })

        return JsonResponse({
            'status': 'ok',
            'amistad_id': solicitud.id,
            'amigos': amigos_list,
        })

    return JsonResponse({'status': 'error'}, status=400)
@login_required
def rechazar_amistad(request, solicitud_id):
    if request.method == "POST" and request.is_ajax():
        solicitud = get_object_or_404(Amistad, id=solicitud_id, para_usuario=request.user)
        solicitud.delete()
        return JsonResponse({'status': 'ok', 'solicitud_id': solicitud_id})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def enviar_solicitud(request, username):
    if request.method != "POST":
        messages.error(request, "Acción no permitida.")
        return redirect('users:perfil_usuario', username=username)

    if username == request.user.username:
        messages.error(request, "No puedes enviarte una solicitud a ti mismo.")
        return redirect('users:perfil_usuario', username=username)

    para_usuario = get_object_or_404(User, username=username)

    ya_existe = Amistad.objects.filter(
        (Q(de_usuario=request.user) & Q(para_usuario=para_usuario)) |
        (Q(de_usuario=para_usuario) & Q(para_usuario=request.user))
    ).exists()

    if ya_existe:
        messages.warning(request, "Ya existe una solicitud o ya sois amigos.")
    else:
        Amistad.objects.create(de_usuario=request.user, para_usuario=para_usuario)
        messages.success(request, "Solicitud enviada correctamente.")

    return redirect('users:perfil_usuario', username=username)

def obtener_amigos(usuario):
    print("Buscando amigos de:", usuario.username)
    amistades = Amistad.objects.filter(
        Q(de_usuario=usuario) | Q(para_usuario=usuario),
        aceptada=True
    )
    print("Amistades encontradas:", amistades)

    amigos = []
    for amistad in amistades:
        print("Amistad:", amistad)
        if amistad.de_usuario == usuario:
            amigos.append(amistad.para_usuario)
        else:
            amigos.append(amistad.de_usuario)
    print("Amigos reales:", amigos)
    return amigos
