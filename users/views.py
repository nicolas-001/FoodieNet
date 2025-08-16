from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from recipes.models import Receta, Favorito  # Ajusta si tu modelo se llama distinto
from .forms import UserEditForm,PerfilForm  # Formulario para editar usuario
from .models import Amistad
from django.contrib import messages
from django.http import JsonResponse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from django.db.models import Q, Count

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

from django.core.paginator import Paginator
from recipes.models import Receta  # importa tu modelo de Receta

def buscar_usuarios_y_recetas(request):
    query = request.GET.get('query')
    
    usuarios = User.objects.none()
    recetas = Receta.objects.none()

    if query:
        usuarios = User.objects.filter(username__icontains=query).order_by('username')
        recetas = Receta.objects.filter(
            titulo__icontains=query
        ).order_by('titulo')

    # Paginación usuarios (10 por página)
    paginator_usuarios = Paginator(usuarios, 10)
    page_number_usuarios = request.GET.get('page_usuarios')
    page_obj_usuarios = paginator_usuarios.get_page(page_number_usuarios)

    # Paginación recetas (opcional, 10 por página)
    paginator_recetas = Paginator(recetas, 10)
    page_number_recetas = request.GET.get('page_recetas')
    page_obj_recetas = paginator_recetas.get_page(page_number_recetas)

    return render(request, 'users/buscar_usuarios_y_recetas.html', {
        'page_obj_usuarios': page_obj_usuarios,
        'page_obj_recetas': page_obj_recetas,
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

try:
    import nltk
    from nltk.corpus import stopwords
    # make sure downloaded in your env: nltk.download('stopwords') (once)
    spanish_stopwords = stopwords.words('spanish')
except Exception:
    spanish_stopwords = None


def obtener_usuarios_similares_ml(usuario_objetivo, usuario_actual=None, top_n=3):
    """
    Devuelve lista de Users (máx top_n) similares a usuario_objetivo basados en
    su contenido (recetas: titulo, descripcion, tags, ingredientes).
    Excluye al usuario_actual y al usuario_objetivo.
    """
    # 1) texto del usuario objetivo (combina todas sus recetas públicas)
    recetas_obj = Receta.objects.filter(autor=usuario_objetivo).prefetch_related('tags')
    texto_objetivo_parts = []
    for r in recetas_obj:
        tags = " ".join(t.name for t in r.tags.all())
        ingredientes = (r.ingredientes or "")
        titulo = (r.titulo or "")
        descripcion = (r.descripcion or "")
        texto_objetivo_parts.append(" ".join([titulo, descripcion, tags, ingredientes]))
    texto_objetivo = " ".join(texto_objetivo_parts).strip()

    if not texto_objetivo:
        # si no hay contenido, devolver lista vacía (o los más populares)
        return list(User.objects.none())

    # 2) construir corpus de otros usuarios que tienen recetas
    otros_usuarios_qs = User.objects.exclude(id=usuario_objetivo.id)
    if usuario_actual:
        otros_usuarios_qs = otros_usuarios_qs.exclude(id=usuario_actual.id)

    # limitar a usuarios que tengan al menos 1 receta para no vectorizar todo
    otros_usuarios_qs = otros_usuarios_qs.annotate(num_recetas=Count('receta')).filter(num_recetas__gt=0)

    usuarios = []
    corpus = []
    for u in otros_usuarios_qs:
        recetas_u = Receta.objects.filter(autor=u).prefetch_related('tags')
        partes = []
        for r in recetas_u:
            tags = " ".join(t.name for t in r.tags.all())
            ingredientes = (r.ingredientes or "")
            titulo = (r.titulo or "")
            descripcion = (r.descripcion or "")
            partes.append(" ".join([titulo, descripcion, tags, ingredientes]))
        texto_u = " ".join(partes).strip()
        if texto_u:
            usuarios.append(u)
            corpus.append(texto_u)

    if not corpus:
        return []

    # 3) Vectorizar (perfil objetivo + corpus)
    # Si spanish_stopwords disponible, úsala; sino no filtrar stopwords
    vectorizer = TfidfVectorizer(stop_words=spanish_stopwords)
    try:
        matriz = vectorizer.fit_transform([texto_objetivo] + corpus)
    except Exception:
        # fallback sin stopwords si algo falla
        vectorizer = TfidfVectorizer(stop_words=None)
        matriz = vectorizer.fit_transform([texto_objetivo] + corpus)

    perfil_vec = matriz[0:1]
    otros_vecs = matriz[1:]

    # 4) calcular similitud coseno
    sims = cosine_similarity(perfil_vec, otros_vecs).flatten()
    # ordenar índices descendente
    idx_sorted = np.argsort(sims)[::-1]
    top_idx = idx_sorted[:top_n]

    usuarios_similares = [usuarios[i] for i in top_idx if sims[i] > 0]

    return usuarios_similares


@login_required
def enviar_solicitud(request, username):
    """
    Envía solicitud de amistad y devuelve recomendaciones ML vía JSON.
    """
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=400)

    if username == request.user.username:
        return JsonResponse({'status': 'error', 'message': 'No puedes enviarte una solicitud a ti mismo.'}, status=400)

    para_usuario = get_object_or_404(User, username=username)

    # Evitar duplicados
    ya_existe = Amistad.objects.filter(
        (Q(de_usuario=request.user) & Q(para_usuario=para_usuario)) |
        (Q(de_usuario=para_usuario) & Q(para_usuario=request.user))
    ).exists()

    if ya_existe:
        return JsonResponse({'status': 'error', 'message': 'Ya existe una solicitud o ya sois amigos.'}, status=400)

    # Crear la solicitud
    Amistad.objects.create(de_usuario=request.user, para_usuario=para_usuario)

    # Obtener recomendaciones ML (excluyendo usuario actual y objetivo)
    usuarios_similares = obtener_usuarios_similares_ml(
        para_usuario,
        usuario_actual=request.user,
        top_n=3
    )

    recomendaciones_data = []
    for u in usuarios_similares:
        recomendaciones_data.append({
            'username': u.username,
            'full_name': getattr(u, 'get_full_name', lambda: "")() or "",
            'perfil_url': f"/users/{u.username}/",  # Ajusta según tus URLs reales
            'foto_url': getattr(getattr(u, 'perfil', None), 'foto.url', '/static/perfiles/default.jpeg'),
        })

    return JsonResponse({
        'status': 'ok',
        'message': 'Solicitud enviada correctamente.',
        'recomendaciones': recomendaciones_data
    })

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


def obtener_usuarios_similares(usuario_objetivo, top_n=3):
    """
    Devuelve una lista de usuarios similares al usuario_objetivo según sus recetas.
    """
    # Obtener todos los usuarios menos el objetivo
    usuarios = User.objects.exclude(id=usuario_objetivo.id)

    # Crear corpus de texto con las recetas de cada usuario
    corpus = []
    user_index_map = []

    for u in usuarios:
        recetas = u.receta_set.all()  # Asumiendo que User → Receta con FK `autor`
        texto = " ".join([
            f"{r.titulo} {r.descripcion} {r.ingredientes} {' '.join(tag.name for tag in r.tags.all())}"
            for r in recetas
        ])
        corpus.append(texto if texto.strip() else "")
        user_index_map.append(u)

    # Corpus del usuario objetivo
    recetas_objetivo = usuario_objetivo.receta_set.all()
    texto_objetivo = " ".join([
        f"{r.titulo} {r.descripcion} {r.ingredientes} {' '.join(tag.name for tag in r.tags.all())}"
        for r in recetas_objetivo
    ])
    corpus.insert(0, texto_objetivo)  # Usuario objetivo al inicio

    # Vectorización TF-IDF
    vectorizer = TfidfVectorizer(stop_words="spanish")
    tfidf_matrix = vectorizer.fit_transform(corpus)

    # Calcular similitudes
    similitudes = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    # Obtener top N usuarios más similares
    indices_similares = similitudes.argsort()[::-1][:top_n]

    return [user_index_map[i] for i in indices_similares]
