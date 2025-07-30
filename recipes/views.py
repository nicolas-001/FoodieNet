# recipes/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import F, Count, Q
from django.contrib.auth.decorators import login_required
from django.views.generic import UpdateView
from django.conf import settings
from django.views.decorators.http import require_GET

from .models import Receta, Like, Favorito, Comentario
from .forms import RecetaForm, ComentarioForm
from users.models import Amistad
from django.core.paginator import Paginator
import os, re
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from recipes.utils.traductor import traducir_ingrediente_a_ingles
from .utils.recomendador import recomendar_recetas
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from ml_models.utils import construir_dataframe_recetas
from ml_models.contenido import ContentBasedRecommender
from django.shortcuts import render
from .helpers import get_recetas_dataframe, limpiar_ingredientes



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

def construir_dataframe_recetas_con_ingredientes():
    recetas = Receta.objects.all().prefetch_related('tags')
    data = []

    for receta in recetas:
        ingredientes_limpios = limpiar_ingredientes(receta.ingredientes)  # tu función de limpieza
        ingredientes_text = ' '.join(ingredientes_limpios)

        tags = [tag.name for tag in receta.tags.all()]

        data.append({
            'id': receta.id,
            'titulo': receta.titulo,
            'tags': tags,
            'ingredientes': ingredientes_limpios,
            'ingredientes_text': ingredientes_text,
            'calorias': receta.calorias or 0,
            'proteinas': receta.proteinas or 0,
            'grasas': receta.grasas or 0,
            'carbohidratos': receta.carbohidratos or 0,
        })

    return pd.DataFrame(data)
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