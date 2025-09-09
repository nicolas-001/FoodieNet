# recipes/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import F, Count, Q, Func
from django.contrib.auth.decorators import login_required
from django.views.generic import UpdateView
from django.conf import settings
from django.views.decorators.http import require_GET, require_POST
from django.utils.dateformat import DateFormat
from datetime import date
from .models import Receta, Like, Favorito, Comentario, PlanDiario, PlatoPersonalizado
from .forms import RecetaForm, ComentarioForm, PlanDiarioForm
from users.models import Amistad
from django.core.paginator import Paginator
import os, re
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from recipes.utils.traductor import traducir_ingrediente_a_ingles
from .utils.recomendador import recomendar_recetas
from .utils.funciones_auxiliares import truncar
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from ml_models.utils import construir_dataframe_recetas
from ml_models.contenido import ContentBasedRecommender
from django.shortcuts import render
from .helpers import get_recetas_dataframe, limpiar_ingredientes
import nltk
from nltk.corpus import stopwords
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from taggit.models import Tag
from django.template.loader import render_to_string
import random

def obtener_recetas_base_para_usuario(usuario, top_n=3):
    liked_recetas = Receta.objects.filter(likes__user=usuario).order_by('-likes__creado')[:top_n]
    if liked_recetas.exists():
        return liked_recetas
    propias = Receta.objects.filter(autor=usuario).order_by('-fecha_creacion')[:top_n]
    if propias.exists():
        return propias
    return []



def lista_recetas(request):
    usuario = request.user
    recomendaciones = []
    tipo_recomendacion = "popular"  # Valor por defecto

    tag_seleccionado = request.GET.get('tag', '')
    dificultad_seleccionada = request.GET.get('dificultad', '')

    if usuario.is_authenticated:
        recomendaciones = obtener_recomendaciones_generales(usuario)
        recomendaciones_ids = [r.id for r in recomendaciones]

        amigos = usuario.perfil.obtener_amigos()
        recetas_qs = Receta.objects.filter(
            (Q(es_publica=True) | Q(es_publica=False, autor__in=amigos)) &
            ~Q(id__in=recomendaciones_ids)
        ).select_related('autor__perfil').distinct().order_by('-fecha_creacion')

        if Like.objects.filter(user=usuario).exists() or Favorito.objects.filter(user=usuario).exists():
            tipo_recomendacion = "likes"

    else:
        recetas_qs = Receta.objects.filter(es_publica=True).select_related('autor__perfil').order_by('-fecha_creacion')

    # Filtrar por tag
    if tag_seleccionado:
        recetas_qs = recetas_qs.filter(tags__name__iexact=tag_seleccionado)

    # Filtrar por dificultad
    if dificultad_seleccionada:
        recetas_qs = recetas_qs.filter(dificultad__iexact=dificultad_seleccionada)

    # Tags disponibles para el filtro
    tags_disponibles = Tag.objects.all().order_by('name')

    # Construir query_params para mantener filtros en la paginación
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_params = query_params.urlencode()

    paginator = Paginator(recetas_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recipes/lista_recetas.html', {
        'page_obj': page_obj,
        'recomendaciones': recomendaciones,
        'tipo_recomendacion': tipo_recomendacion,
        'tags_disponibles': tags_disponibles,
        'tag_seleccionado': tag_seleccionado,
        'dificultad_seleccionada': dificultad_seleccionada,
        'query_params': query_params
    })

def lista_recetas_ajax(request):
    usuario = request.user
    tag_filtro = request.GET.get('tag', '')
    dificultad_filtro = request.GET.get('dificultad', '')

    recetas_qs = Receta.objects.all().select_related('autor__perfil').order_by('-fecha_creacion')

    if usuario.is_authenticated:
        recomendaciones_ids = [r.id for r in obtener_recomendaciones_generales(usuario)]
        amigos = usuario.perfil.obtener_amigos()
        recetas_qs = recetas_qs.filter(
            (Q(es_publica=True) | Q(es_publica=False, autor__in=amigos)) &
            ~Q(id__in=recomendaciones_ids)
        )

    # Aplicar filtros
    if tag_filtro:
        recetas_qs = recetas_qs.filter(tags__name__iexact=tag_filtro)
    if dificultad_filtro:
        recetas_qs = recetas_qs.filter(dificultad__iexact=dificultad_filtro)

    paginator = Paginator(recetas_qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    html = render_to_string('recipes/_recetas_lista.html', {'page_obj': page_obj})
    return JsonResponse({'html': html, 'num_pages': paginator.num_pages, 'current_page': page_obj.number})

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

    tags = receta.tags.all()  # <---- LÍNEA AÑADIDA

    return render(request, 'recipes/detalle_receta.html', {
        'receta': receta,
        'liked': liked,
        'favorited': favorited,
        'form': form,
        'comentarios': comentarios,
        'tags': tags,   # <---- LÍNEA AÑADIDA
    })

@login_required
def crear_receta(request):
    if request.method == 'POST':
        form = RecetaForm(request.POST, request.FILES)
        if form.is_valid():
            nueva = form.save(commit=False)
            nueva.autor = request.user
            try:
                nueva.save()
                print("Receta guardada correctamente con ID:", nueva.pk)
            except Exception as e:
                print("Error guardando receta:", e)
            return redirect('detalle_receta', pk=nueva.pk)
        else:
            print("Formulario no válido:", form.errors)
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
    receta = get_object_or_404(Receta, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, receta=receta)

    if not created:
        like.delete()

    # Cuenta total de likes actualizada
    total_likes = receta.likes.count()

    # Si es una petición AJAX, devolvemos JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'liked': created,
            'total_likes': total_likes
        })

    # Si no es AJAX, redirige como siempre
    return redirect('detalle_receta', pk=pk)
@login_required
@require_POST

def toggle_favorito(request, pk):
    receta = get_object_or_404(Receta, pk=pk)
    user = request.user

    favorito, creado = Favorito.objects.get_or_create(user=user, receta=receta)
    if not creado:
        favorito.delete()
        status = "removed"
    else:
        status = "added"

    # Contar favoritos actualizados
    total_favoritos = Favorito.objects.filter(receta=receta).count()

    return JsonResponse({
        "favorited": status == "added",
        "status": status,
        "total_favoritos": total_favoritos,
    })
@login_required
def feed_amigos(request):
    # Obtener amistades aceptadas
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

    # Obtener recetas de amigos
    recetas = Receta.objects.filter(
        autor__id__in=amigos_ids
    ).order_by('-fecha_creacion')

    # FILTROS
    tag_seleccionado = request.GET.get('tag')
    dificultad_seleccionada = request.GET.get('dificultad')

    if tag_seleccionado and tag_seleccionado != "todos":
        recetas = recetas.filter(tags__name__in=[tag_seleccionado])

    if dificultad_seleccionada and dificultad_seleccionada != "todas":
        recetas = recetas.filter(dificultad=dificultad_seleccionada)

    # Obtener todos los tags disponibles para las recetas filtradas
    tags_disponibles = Tag.objects.filter(receta__in=recetas).distinct()

    # PAGINACIÓN: 10 recetas por página
    paginator = Paginator(recetas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Guardar los parámetros de filtro en la plantilla para que persistan al paginar
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')

    return render(request, 'recipes/feed_amigos.html', {
        'page_obj': page_obj,
        'tags_disponibles': tags_disponibles,
        'tag_seleccionado': tag_seleccionado,
        'dificultad_seleccionada': dificultad_seleccionada,
        'query_params': query_params.urlencode(),
    })

import os, unicodedata
import requests, json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from .models import Receta

def limpiar_y_dividir_ingredientes(ingredientes_lista):
    nuevos_ingredientes = []
    for ing in ingredientes_lista:
        if " o " in ing.lower():
            partes = ing.lower().split(" o ")
            for parte in partes:
                parte_limpia = parte.strip().capitalize()
                nuevos_ingredientes.append(parte_limpia)
        else:
            nuevos_ingredientes.append(ing)
    return nuevos_ingredientes

def obtener_info_nutricional_spoonacular(ingredientes_lista, api_key):
    url = "https://api.spoonacular.com/recipes/parseIngredients"

    # Traducción previa al inglés
    ingredientes_traducidos = [traducir_ingrediente_a_ingles(ing) for ing in ingredientes_lista]

    ingredientes_como_texto = "\n".join(ingredientes_traducidos)
    payload = {
        "ingredientList": ingredientes_como_texto,
        "servings": 1,
        "includeNutrition": True
    }

    params = {
        "apiKey": api_key
    }

    try:
        print(f"[DEBUG] Enviando a Spoonacular:\nPayload={payload}\nParams={params}")
        response = requests.post(url, params=params, data=payload)
        print(f"[DEBUG] Código de respuesta: {response.status_code}")
        if len(response.text) > 500:
            print(f"[DEBUG] Respuesta (recortada): {response.text[:500]}...")
        else:
            print(f"[DEBUG] Respuesta completa: {response.text}")
    except requests.RequestException as e:
        print(f"[Error conexión Spoonacular] {e}")
        return None

    if response.status_code == 200:
        try:
            data = response.json()
        except Exception as e:
            print(f"[Error parsing JSON Spoonacular] {e}")
            return None

        resultado = {
            "calorias_totales": 0,
            "proteinas_totales": 0,
            "grasas_totales": 0,
            "carbohidratos_totales": 0,
            "ingredientes": []
        }

        for idx, ingrediente in enumerate(data):
            nutr = ingrediente.get("nutrition", {})
            nutrientes = nutr.get("nutrients", [])
            calorias = next((n["amount"] for n in nutrientes if n["name"] == "Calories"), 0)
            proteinas = next((n["amount"] for n in nutrientes if n["name"] == "Protein"), 0)
            grasas = next((n["amount"] for n in nutrientes if n["name"] == "Fat"), 0)
            carbs = next((n["amount"] for n in nutrientes if n["name"] == "Carbohydrates"), 0)

            resultado["calorias_totales"] += calorias
            resultado["proteinas_totales"] += proteinas
            resultado["grasas_totales"] += grasas
            resultado["carbohidratos_totales"] += carbs

            cantidad = ingrediente.get("amount", 0)
            unidad = ingrediente.get("unit", "")
            cantidad_texto = f"{cantidad} {unidad}".strip()

            # Nombre original en español
            nombre_original = ingredientes_lista[idx]

            resultado["ingredientes"].append({
                "nombre": nombre_original,
                "cantidad": cantidad_texto,
                "calorias": calorias,
                "proteinas": proteinas,
                "grasas": grasas,
                "carbohidratos": carbs
            })

        print(f"[DEBUG] Resultado parseado: {resultado}")
        return resultado

    else:
        print(f"[Error Spoonacular] Código: {response.status_code} - Respuesta: {response.text}")
        return None

    

@require_GET
def calcular_calorias_macros(request, receta_id):
    receta = get_object_or_404(Receta, id=receta_id)

    api_key = os.getenv('SPOONACULAR_API_KEY')
    if not api_key:
        print("API key no configurada")
        return JsonResponse({'error': 'API key no configurada'}, status=500)

    texto_ingredientes = receta.ingredientes.strip()
    if not texto_ingredientes:
        print("No hay ingredientes para analizar")
        return JsonResponse({'error': 'No hay ingredientes para analizar'}, status=400)

    ingredientes_lista = [linea.strip() for linea in texto_ingredientes.splitlines() if linea.strip()]
    print(f"[DEBUG] Ingredientes antes de limpiar y dividir: {ingredientes_lista}")

    ingredientes_lista = limpiar_y_dividir_ingredientes(ingredientes_lista)
    print(f"[DEBUG] Ingredientes después de limpiar y dividir: {ingredientes_lista}")

    detalle = obtener_info_nutricional_spoonacular(ingredientes_lista, api_key)
    if detalle is None:
        print("Error al obtener info nutricional de Spoonacular")
        return JsonResponse({'error': 'Error en la API de Spoonacular o API key inválida'}, status=500)

    print(f"Guardando datos nutricionales en la receta {receta_id}: {detalle}")
    receta.calorias = detalle["calorias_totales"]
    receta.proteinas = detalle["proteinas_totales"]
    receta.grasas = detalle["grasas_totales"]
    receta.carbohidratos = detalle["carbohidratos_totales"]
    receta.save()

    return JsonResponse({
        'status': 'ok',
        'calorias': detalle["calorias_totales"],
        'proteinas': detalle["proteinas_totales"],
        'grasas': detalle["grasas_totales"],
        'carbohidratos': detalle["carbohidratos_totales"],
        'detalle_por_ingrediente': detalle["ingredientes"]
    })


def normalizar_texto(texto):
    """
    Elimina tildes y convierte a minúsculas para comparar de forma flexible.
    """
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto

def recomendador_por_ingredientes(ingredientes_query):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    recetas = Receta.objects.all()
    ingredientes_list = [r.ingredientes for r in recetas]

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(ingredientes_list)

    query_vec = vectorizer.transform([ingredientes_query])
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()

    top_indices = similarities.argsort()[::-1][:5]
    # convertir los índices numpy a int nativos de Python
    top_recetas = [recetas[int(i)] for i in top_indices]

    return top_recetas

def probar_recomendador(request):
    query = request.GET.get('ingredientes', '')  # ejemplo: "harina queso tomate"
    recetas_recomendadas = []
    if query:
        recetas_recomendadas = recomendador_por_ingredientes(query)

    return render(request, 'recipes/feed_recomendaciones.html', {
        'recetas': recetas_recomendadas,
        'query': query
    })
@require_http_methods(["GET", "POST"])
def seleccionar_ingredientes(request):
    if request.method == "POST":
        ingredientes = request.POST.get('ingredientes', '')
        return redirect(f'/probar_recomendador/?ingredientes={ingredientes}')
    return render(request, 'recipes/seleccionar_ingredientes.html')

def limpiar_tiempo_preparacion(valor):
    """Extrae el primer número entero del valor (por ejemplo '60 minutos' → 60)."""
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return valor
    match = re.search(r'\d+', str(valor))
    if match:
        return int(match.group())
    return None

def construir_dataframe_recetas_con_ingredientes():
    recetas = Receta.objects.all().prefetch_related('tags')
    
    data = []
    for receta in recetas:
        ingredientes_texto = receta.ingredientes if isinstance(receta.ingredientes, str) else ""
        tags = list(receta.tags.names()) if receta.tags else []

        data.append({
            'id': receta.id,
            'titulo': receta.titulo,
            'ingredientes_text': ingredientes_texto,
            'tags': tags,
            'calorias': receta.calorias,
            'proteinas': receta.proteinas,
            'grasas': receta.grasas,
            'carbohidratos': receta.carbohidratos,
            'tiempo_preparacion': limpiar_tiempo_preparacion(receta.tiempo_preparacion),
        })

    df = pd.DataFrame(data)
    return df
def get_recetas_dataframe():
    qs = Receta.objects.all().values(
        'id', 'titulo', 'tags', 'calorias', 'proteinas', 'grasas', 'carbohidratos'
    )
    df = pd.DataFrame.from_records(qs)

    # Asegúrate que 'tags' es una lista de strings, ajusta según cómo almacenas las etiquetas
    df['tags'] = df['tags'].apply(lambda x: x if isinstance(x, list) else [])

    return df

def vista_recomendar_recetas(request, receta_id):
    df = construir_dataframe_recetas_con_ingredientes()

    recomendador = ContentBasedRecommender(df)
    recomendador.preprocess()
    recomendaciones = recomendador.recomendar_similares(receta_id, top_n=5)

    ids_recomendados = recomendaciones['id'].tolist()
    recetas_recomendadas = list(Receta.objects.filter(id__in=ids_recomendados))
    recetas_recomendadas.sort(key=lambda x: ids_recomendados.index(x.id))

    # Igual que antes, manejar likes y favoritos
    user = request.user
    likes_usuario = set()
    favoritos_usuario = set()

    if user.is_authenticated:
        likes_usuario = set(
            Like.objects.filter(user=user, receta__in=recetas_recomendadas)
            .values_list('receta_id', flat=True)
        )
        favoritos_usuario = set(
            Favorito.objects.filter(user=user, receta__in=recetas_recomendadas)
            .values_list('receta_id', flat=True)
        )

    context = {
        "receta_base": Receta.objects.get(id=receta_id),
        "recetas_recomendadas": recetas_recomendadas,
        "likes_usuario": likes_usuario,
        "favoritos_usuario": favoritos_usuario,
    }

    return render(request, "recipes/recomendaciones.html", context)

def recomendaciones_dinamicas(request, receta_id):
    df = construir_dataframe_recetas_con_ingredientes()
    recomendador = ContentBasedRecommender(df)
    recomendador.preprocess()

    recomendaciones = recomendador.recomendar_similares(receta_id, top_n=3)
    ids_recomendados = recomendaciones['id'].tolist()

    recetas_queryset = Receta.objects.filter(id__in=ids_recomendados)
    recetas_dict = {r.id: r for r in recetas_queryset}  # Para mantener el orden del DataFrame

    data = []
    for rec_id in ids_recomendados:
        receta = recetas_dict.get(rec_id)
        if receta:
            data.append({
                'id': receta.id,
                'titulo': receta.titulo,
                'imagen_url': receta.imagen.url if receta.imagen else '',
                'url': receta.get_absolute_url() if hasattr(receta, 'get_absolute_url') else f"/recetas/{receta.id}/",
                'autor_username': receta.autor.username,
                'fecha_creacion': DateFormat(receta.fecha_creacion).format("d M Y"),
            })

    return JsonResponse({'recomendaciones': data})

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import Receta, Like, Favorito

nltk.download('stopwords')

def obtener_recomendaciones_generales(user, top_n=3, pool_size=10):
    """
    Obtiene recomendaciones dinámicas para el usuario:
    - top_n: número de recetas a mostrar
    - pool_size: tamaño del conjunto de recetas relevantes para rotar
    """
    # 1. Obtener IDs de recetas que el usuario ha marcado con like y favorito
    recetas_liked_ids = Like.objects.filter(user=user).values_list('receta_id', flat=True)
    recetas_fav_ids = Favorito.objects.filter(user=user).values_list('receta_id', flat=True)
    recetas_ids = list(set(recetas_liked_ids) | set(recetas_fav_ids))

    # 2. Excluir recetas del propio usuario
    recetas_ids_autor = Receta.objects.filter(autor=user).values_list('id', flat=True)
    recetas_ids = list(set(recetas_ids) - set(recetas_ids_autor))

    # 3. Recetas base si no tiene likes ni favoritos
    if not recetas_ids:
        base_recetas = obtener_recetas_base_para_usuario(user, top_n=pool_size)
        if base_recetas:
            return random.sample(list(base_recetas), min(top_n, len(base_recetas)))
        return list(Receta.objects.filter(es_publica=True).exclude(autor=user).order_by('-visitas')[:top_n])

    recetas_usuario = Receta.objects.filter(id__in=recetas_ids)
    spanish_stopwords = stopwords.words('spanish')

    # Corpus de texto (tags + ingredientes)
    def get_corpus(receta):
        tags = " ".join(tag.name for tag in receta.tags.all())
        ingredientes = receta.ingredientes or ""
        return f"{tags} {ingredientes}"

    perfil_texto = " ".join(get_corpus(r) for r in recetas_usuario)

    # Todas las recetas públicas no propias y no ya en likes/favoritos
    recetas_publicas = Receta.objects.filter(es_publica=True).exclude(Q(id__in=recetas_ids) | Q(autor=user))
    if not recetas_publicas.exists():
        return []

    corpus_recetas = [get_corpus(r) for r in recetas_publicas]

    # Vectorizamos perfil y corpus
    vectorizer = TfidfVectorizer(stop_words=spanish_stopwords)
    vectores = vectorizer.fit_transform([perfil_texto] + corpus_recetas)
    perfil_vector = vectores[0]
    recetas_vectors = vectores[1:]

    similitudes = cosine_similarity(perfil_vector, recetas_vectors).flatten()
    recetas_similares = list(zip(recetas_publicas, similitudes))
    recetas_similares.sort(key=lambda x: x[1], reverse=True)

    # Tomamos un pool más grande de recetas relevantes
    pool = [r[0] for r in recetas_similares[:pool_size]]

    # Si faltan para llenar el pool, completamos con la función auxiliar
    faltantes = pool_size - len(pool)
    if faltantes > 0:
        recetas_resto = obtener_recetas_base_para_usuario(user, top_n=faltantes)
        pool.extend(list(recetas_resto))

    # Finalmente, rotamos seleccionando aleatoriamente 'top_n' recetas del pool
    recomendaciones = random.sample(pool, min(top_n, len(pool)))

    return recomendaciones



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buscar_recetas(request):
    query = request.GET.get('search', '').strip()
    if not query:
        return Response([])  # devolvemos lista vacía si no hay query

    recetas = Receta.objects.filter(titulo__icontains=query, es_publica=True)[:20]

    resultados = []
    for r in recetas:
        resultados.append({
            'id': r.id,
            'titulo': r.titulo,
            'imagen': r.imagen.url if r.imagen else None,
            # usamos macros por persona
            'calorias': r.calorias_por_persona or 0,
            'proteinas': r.proteinas_por_persona or 0,
            'grasas': r.grasas_por_persona or 0,
            'carbohidratos': r.carbohidratos_por_persona or 0,
        })

    return Response(resultados)


@login_required
def crear_plan_diario(request):
    if request.method == 'POST':
        form = PlanDiarioForm(request.POST, usuario=request.user)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.usuario = request.user
            plan.save()
            form.save_m2m()

            # Guardar platos personalizados
            nombres = request.POST.getlist("plato_nombre[]")
            calorias = request.POST.getlist("plato_calorias[]")
            proteinas = request.POST.getlist("plato_proteinas[]")
            grasas = request.POST.getlist("plato_grasas[]")
            carbohidratos = request.POST.getlist("plato_carbohidratos[]")

            for i in range(len(nombres)):
                if nombres[i].strip():  # evitar vacíos
                    PlatoPersonalizado.objects.create(
                        plan=plan,  # <--- asignar plan
                        nombre=nombres[i],
                        calorias=float(calorias[i]) if calorias[i] else 0,
                        proteinas=float(proteinas[i]) if proteinas[i] else 0,
                        grasas=float(grasas[i]) if grasas[i] else 0,
                        carbohidratos=float(carbohidratos[i]) if carbohidratos[i] else 0,
                    )

            plan.calcular_totales()  # recalcular totales con recetas + platos personalizados
            return redirect('users:dashboard')
    else:
        form = PlanDiarioForm(usuario=request.user)

    return render(request, 'recipes/crear_plan_diario.html', {'form': form})





@login_required
@login_required
def ver_plan_diario(request, pk):
    plan = get_object_or_404(PlanDiario, pk=pk, usuario=request.user)

    total_calorias = plan.calorias_totales
    total_prot = plan.proteinas_totales
    total_grasas = plan.grasas_totales
    total_carbs = plan.carbohidratos_totales

    perfil = getattr(request.user, "perfil", None)
    tdee = None
    estado = "No disponible"
    recomendaciones = []
    sugerencias_objetivo = []

    if perfil:
        peso = perfil.peso or 70
        altura = perfil.altura or 170
        edad = perfil.edad or 25
        sexo = perfil.sexo or "M"

        if sexo == "M":
            bmr = 10 * peso + 6.25 * altura - 5 * edad + 5
        else:
            bmr = 10 * peso + 6.25 * altura - 5 * edad - 161

        factor_actividad = getattr(perfil, "factor_actividad", 1.5)
        tdee = round(bmr * factor_actividad, 1)

        diferencia = total_calorias - tdee

        # --- Estado y recomendaciones generales ---
        if diferencia < -500:
            estado = "Déficit calórico"
            recomendaciones.append(f"Déficit agresivo: aumenta ~{abs(diferencia)-500} kcal para un déficit moderado.")
        elif -500 <= diferencia <= -200:
            estado = "Déficit calórico"
            recomendaciones.append("Déficit moderado adecuado para perder grasa sosteniblemente.")
        elif -200 < diferencia < 200:
            estado = "Mantenimiento"
            recomendaciones.append("Calorías cerca de tu TDEE, ideal para mantener el peso.")
        elif 200 <= diferencia <= 500:
            estado = "Superávit calórico"
            recomendaciones.append("Superávit moderado, ideal para ganar músculo controladamente.")
        elif diferencia > 500:
            estado = "Superávit calórico"
            recomendaciones.append(f"Superávit alto: reduce ~{diferencia-500} kcal para volumen más controlado.")

        # --- Evaluación de macros ---
        prot_min = round(1.6 * peso, 1)
        prot_max = round(2.2 * peso, 1)
        if total_prot < prot_min:
            recomendaciones.append(f"Proteínas bajas: añade {prot_min - total_prot:.1f} g más al día.")
        elif total_prot > prot_max:
            recomendaciones.append("Proteínas algo altas: no necesitas tanto para progresar.")

        grasas_kcal = total_grasas * 9
        grasas_pct = (grasas_kcal / total_calorias * 100) if total_calorias else 0
        if grasas_pct < 20:
            recomendaciones.append("Grasas muy bajas: añade frutos secos, aceite de oliva o aguacate.")
        elif grasas_pct > 35:
            recomendaciones.append("Grasas algo altas: reduce fritos o comidas grasientas.")

        carbs_kcal = total_carbs * 4
        if total_calorias > 0:
            carbs_pct = (carbs_kcal / total_calorias * 100)
            if carbs_pct < 40:
                recomendaciones.append("Carbohidratos bajos: añade más arroz, pasta, pan o frutas.")
            elif carbs_pct > 60:
                recomendaciones.append("Carbohidratos altos: equilibra con más proteínas y grasas saludables.")

        # --- Recomendaciones Premium con calorías explícitas ---
        ids_recetas_plan = plan.recetas.values_list('id', flat=True)

        if diferencia < -50:  # Déficit: sugerir añadir calorías
            kcal_faltantes = abs(diferencia)
            receta_sugerida = (
                Receta.objects.exclude(id__in=ids_recetas_plan)
                .filter(calorias__lte=kcal_faltantes + 50)
                .annotate(diferencia_abs=Func(F('calorias') - kcal_faltantes, function='ABS'))
                .order_by('diferencia_abs')
                .first()
            )
            if receta_sugerida:
                sugerencias_objetivo.append({
                    "tipo": "añadir",
                    "receta": receta_sugerida,
                    "kcal_objetivo": kcal_faltantes,
                    "kcal_receta": receta_sugerida.calorias_por_persona
                })

        elif diferencia > 50:  # Superávit: sugerir sustituir para bajar calorías
            receta_a_reducir = (
                plan.recetas.filter(calorias__gte=diferencia)
                .order_by('-calorias')
                .first()
            )
            if receta_a_reducir:
                receta_sustituta = (
                    Receta.objects.exclude(id__in=ids_recetas_plan)
                    .filter(calorias__lt=receta_a_reducir.calorias)
                    .annotate(diferencia_abs=Func(F('calorias') - receta_a_reducir.calorias, function='ABS'))
                    .order_by('diferencia_abs')
                    .first()
                )
                if receta_sustituta:
                    kcal_reducidas = receta_a_reducir.calorias_por_persona - receta_sustituta.calorias_por_persona
                    sugerencias_objetivo.append({
                        "tipo": "sustituir",
                        "receta_original": receta_a_reducir,
                        "receta_sugerida": receta_sustituta,
                        "kcal_objetivo": diferencia,
                        "kcal_reducidas": kcal_reducidas
                    })

    context = {
        "plan": plan,
        "total_calorias": total_calorias,
        "total_prot": total_prot,
        "total_grasas": total_grasas,
        "total_carbs": total_carbs,
        "tdee": tdee,
        "estado": estado,
        "recomendaciones": recomendaciones,
        "sugerencias_objetivo": sugerencias_objetivo,
    }

    return render(request, "recipes/ver_plan_diario.html", context)


@login_required
def listar_planes_diarios(request):
    planes = PlanDiario.objects.filter(usuario=request.user).order_by("-fecha")
    return render(request, "recipes/listar_planes_diarios.html", {"planes": planes})

@login_required
def editar_plan_diario(request, pk):
    plan = get_object_or_404(PlanDiario, pk=pk, usuario=request.user)
    if request.method == "POST":
        form = PlanDiarioForm(request.POST, instance=plan, usuario=request.user)
        if form.is_valid():
            plan = form.save()
            plan.calcular_totales()
            return redirect("users:dashboard")
    else:
        form = PlanDiarioForm(instance=plan, usuario=request.user)

    return render(request, "recipes/editar_plan_diario.html", {"form": form, "plan": plan})


@login_required
def eliminar_plan_diario(request, pk):
    plan = get_object_or_404(PlanDiario, pk=pk, usuario=request.user)
    if request.method == "POST":
        plan.delete()
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error", "msg": "Método no permitido"}, status=405)

@login_required
def receta_info_json(request, receta_id):
    receta = get_object_or_404(Receta, id=receta_id)
    data = {
        "id": receta.id,
        "titulo": receta.titulo,
        "calorias": receta.calorias_por_persona,
        "proteinas": receta.proteinas_por_persona,
        "grasas": receta.grasas_por_persona,
        "carbohidratos": receta.carbohidratos_por_persona,
    }
    return JsonResponse(data)

