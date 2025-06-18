from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from recipes.models import Receta, Favorito  # Ajusta si tu modelo se llama distinto
from .forms import UserEditForm,PerfilForm  # Formulario para editar usuario
from .models import Amistad
from django.contrib import messages


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
    amigos = obtener_amigos(request.user)

    return render(
        request,
        'users/perfil.html',
        {
            'form_user': form_user,
            'form_perfil': form_perfil,
            'favoritos': favoritos,
            'amigos': amigos,
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

def buscar_usuarios(request):
    query = request.GET.get('query')
    resultados = []

    if query:
        resultados = User.objects.filter(username__icontains=query)

    return render(request, 'users/buscar_usuarios.html', {
        'resultados': resultados,
        'query': query
    })



def perfil_usuario(request, username):
    otro = get_object_or_404(User, username=username)
    perfil_otro = otro.perfil
    recetas_otro = otro.receta_set

    amigos = obtener_amigos(otro)  # 👈 Aquí obtenemos los amigos del perfil que estamos viendo

    if request.user.is_authenticated:
        if request.user.perfil.amigos.filter(pk=perfil_otro.pk).exists():
            recetas = recetas_otro.all()
            template = 'users/perfil_amigo.html'
        else:
            recetas = recetas_otro.filter(es_publica=True)
            template = 'users/perfil_privado.html'
    else:
        recetas = recetas_otro.filter(es_publica=True)
        template = 'users/perfil_privado.html'

    return render(request, template, {
        'otro': otro,
        'perfil_otro': perfil_otro,
        'recetas': recetas,
        'amigos': amigos  
    })
@login_required
def solicitudes_amistad(request):
    solicitudes = Amistad.objects.filter(para_usuario=request.user, aceptada=False)
    return render(request, 'users/solicitudes_amistad.html', {'solicitudes': solicitudes})

@login_required
def aceptar_amistad(request, amistad_id):
    amistad = get_object_or_404(Amistad, id=amistad_id, para_usuario=request.user)
    amistad.aceptada = True
    amistad.save()
    return redirect('users:solicitudes_amistad')

@login_required
def rechazar_amistad(request, amistad_id):
    amistad = get_object_or_404(Amistad, id=amistad_id, para_usuario=request.user)
    amistad.delete()
    return redirect('users:solicitudes_amistad')

@login_required
def enviar_solicitud(request, username):
    if username == request.user.username:
        messages.error(request, "No puedes enviarte una solicitud a ti mismo.")
        return redirect('users:perfil_usuario', username=username)

    para_usuario = get_object_or_404(User, username=username)

    ya_existe = Amistad.objects.filter(
        de_usuario=request.user,
        para_usuario=para_usuario
    ).exists() or Amistad.objects.filter(
        de_usuario=para_usuario,
        para_usuario=request.user
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
