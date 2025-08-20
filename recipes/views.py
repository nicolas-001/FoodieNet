# recipes/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import F, Count, Q
from django.contrib.auth.decorators import login_required
from django.views.generic import UpdateView
from django.conf import settings
from django.views.decorators.http import require_GET, require_POST
from django.utils.dateformat import DateFormat
from datetime import date
from .models import Receta, Like, Favorito, Comentario, PlanDiario
from .forms import RecetaForm, ComentarioForm, PlanDiarioForm
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
import nltk
from nltk.corpus import stopwords

def obtener_recetas_base_para_usuario(usuario, top_n=2):
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

    if usuario.is_authenticated:
        # Obtener recomendaciones generales (usando ML con favoritos y likes)
        recomendaciones = obtener_recomendaciones_generales(usuario)

        # IDs de recetas recomendadas para excluirlas de la lista general
        recomendaciones_ids = [r.id for r in recomendaciones]

        amigos = usuario.perfil.obtener_amigos()
        recetas_qs = Receta.objects.filter(
            (Q(es_publica=True) | Q(es_publica=False, autor__in=amigos)) &
            ~Q(id__in=recomendaciones_ids)  # Excluimos las recomendaciones
        ).select_related('autor__perfil').distinct().order_by('-fecha_creacion')

    else:
        recomendaciones = []
        recetas_qs = Receta.objects.filter(es_publica=True).select_related('autor__perfil').order_by('-fecha_creacion')

    paginator = Paginator(recetas_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'recipes/lista_recetas.html', {
        'page_obj': page_obj,
        'recomendaciones': recomendaciones,
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

def obtener_recomendaciones_generales(user):
    # 1. Obtener IDs de recetas que el usuario ha marcado con like y favorito
    recetas_liked_ids = Like.objects.filter(user=user).values_list('receta_id', flat=True)
    recetas_fav_ids = Favorito.objects.filter(user=user).values_list('receta_id', flat=True)
    recetas_ids = list(set(recetas_liked_ids) | set(recetas_fav_ids))

    if not recetas_ids:
        # Si no tiene likes ni favoritos, devolvemos las recetas más populares o recientes
        return Receta.objects.filter(es_publica=True).order_by('-visitas')[:3]

    # 2. Obtener recetas del usuario para formar perfil
    recetas_usuario = Receta.objects.filter(id__in=recetas_ids)
    spanish_stopwords = stopwords.words('spanish')
    # 3. Crear corpus de texto para ML (tags + ingredientes)
    # Concatenamos tags y ingredientes para cada receta
    def get_corpus(receta):
        tags = " ".join(tag.name for tag in receta.tags.all())
        ingredientes = receta.ingredientes or ""
        return f"{tags} {ingredientes}"

    perfil_texto = " ".join(get_corpus(r) for r in recetas_usuario)

    # 4. Obtener todas las recetas públicas (menos las que el usuario ya tiene liked/favorito)
    recetas_publicas = Receta.objects.filter(es_publica=True).exclude(id__in=recetas_ids)

    if not recetas_publicas.exists():
        return []

    corpus_recetas = [get_corpus(r) for r in recetas_publicas]

    # 5. Vectorizamos perfil y corpus con Tfidf
    vectorizer = TfidfVectorizer(stop_words=spanish_stopwords)
    vectores = vectorizer.fit_transform([perfil_texto] + corpus_recetas)

    perfil_vector = vectores[0]
    recetas_vectors = vectores[1:]

    # 6. Calcular similitud coseno
    similitudes = cosine_similarity(perfil_vector, recetas_vectors).flatten()

    # 7. Empaquetar resultados con IDs y similitud
    recetas_similares = list(zip(recetas_publicas, similitudes))

    # 8. Ordenar por similitud descendente
    recetas_similares.sort(key=lambda x: x[1], reverse=True)

    # 9. Devolver solo las top 3 recomendaciones
    recomendaciones = [r[0] for r in recetas_similares[:3]]

    return recomendaciones

@login_required
def crear_plan_diario(request):
    if request.method == 'POST':
        form = PlanDiarioForm(request.POST, usuario=request.user)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.usuario = request.user
            plan.save()
            form.save_m2m()  # Esto guarda correctamente las recetas seleccionadas
            plan.calcular_totales()  # Actualiza totales
            return redirect('listar_planes_diarios')  # Cambia por la vista correcta
    else:
        form = PlanDiarioForm(usuario=request.user)

    recetas = Receta.objects.all()
    return render(request, "recipes/crear_plan_diario.html", {"form": form, "recetas": recetas})

@login_required

@login_required
def ver_plan_diario(request, pk):
    plan = get_object_or_404(PlanDiario, pk=pk, usuario=request.user)

    # Usamos valores precalculados en el modelo
    total_calorias = plan.calorias_totales
    total_prot = plan.proteinas_totales
    total_grasas = plan.grasas_totales
    total_carbs = plan.carbohidratos_totales

    perfil = getattr(request.user, "perfil", None)
    tdee = None
    estado = "No disponible"
    recomendacion = None

    if perfil:
        peso = perfil.peso or 70
        altura = perfil.altura or 170
        edad = perfil.edad or 25
        sexo = perfil.sexo or "M"

        # Fórmula Mifflin-St Jeor
        if sexo == "M":
            bmr = 10 * peso + 6.25 * altura - 5 * edad + 5
        else:
            bmr = 10 * peso + 6.25 * altura - 5 * edad - 161

        factor_actividad = getattr(perfil, "factor_actividad", 1.5)
        tdee = round(bmr * factor_actividad, 1)

        # Diferencia calórica
        diferencia = total_calorias - tdee

        # Estado y recomendaciones
        if diferencia < -500:
            estado = "Déficit calórico"
            recomendacion = "Tu déficit es demasiado agresivo. Considera aumentar unas {} kcal para estar en un déficit moderado.".format(abs(diferencia) - 500)
        elif -500 <= diferencia <= -200:
            estado = "Déficit calórico"
            recomendacion = "Buen déficit moderado para perder grasa de forma sostenible."
        elif -200 < diferencia < 200:
            estado = "Mantenimiento"
            recomendacion = "Tus calorías están cerca de tu gasto, ideal para mantener el peso."
        elif 200 <= diferencia <= 500:
            estado = "Superávit calórico"
            recomendacion = "Buen superávit moderado para ganar músculo sin excesiva grasa."
        elif diferencia > 500:
            estado = "Superávit calórico"
            recomendacion = "Tu superávit es muy alto. Reduce unas {} kcal para un volumen más controlado.".format(diferencia - 500)

    context = {
        "plan": plan,
        "total_calorias": total_calorias,
        "total_prot": total_prot,
        "total_grasas": total_grasas,
        "total_carbs": total_carbs,
        "tdee": tdee,
        "estado": estado,
        "recomendacion": recomendacion,
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
            return redirect("listar_planes_diarios")
    else:
        form = PlanDiarioForm(instance=plan, usuario=request.user)

    return render(request, "recipes/editar_plan_diario.html", {"form": form, "plan": plan})


@login_required
def eliminar_plan_diario(request, pk):
    plan = get_object_or_404(PlanDiario, pk=pk, usuario=request.user)
    if request.method == "POST":
        plan.delete()
        return redirect("listar_planes_diarios")
    return render(request, "recipes/eliminar_plan_diario.html", {"plan": plan})

