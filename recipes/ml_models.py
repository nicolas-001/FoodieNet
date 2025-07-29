from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter
import numpy as np

# Asumo que importas tus modelos Django aquí
from .models import Receta, User, Like, Amigo  # Ajusta según nombres reales


class RecomendadorRecetas:
    def __init__(self):
        self.vectorizer = None
        self.tfidf_matrix = None
        self.recetas = None
        self.id_to_index = {}

    def entrenar_modelo_contenido(self):
        # Recoger texto de cada receta: ingredientes + nombre + descripción
        self.recetas = list(Receta.objects.all())
        textos = [
            f"{r.nombre} {r.descripcion} {' '.join(r.ingredientes)}"
            for r in self.recetas
        ]
        self.vectorizer = TfidfVectorizer(stop_words='spanish')
        self.tfidf_matrix = self.vectorizer.fit_transform(textos)
        self.id_to_index = {r.id: i for i, r in enumerate(self.recetas)}

    def recomendar_similares(self, receta_obj, top_n=5):
        if self.tfidf_matrix is None:
            self.entrenar_modelo_contenido()
        idx = self.id_to_index.get(receta_obj.id)
        if idx is None:
            return []
        cosine_sim = cosine_similarity(self.tfidf_matrix[idx], self.tfidf_matrix).flatten()
        # Ignorar la receta misma:
        cosine_sim[idx] = 0
        indices_similares = cosine_sim.argsort()[-top_n:][::-1]
        return [self.recetas[i] for i in indices_similares]

    def recomendar_por_usuario(self, usuario, top_n=10):
        # Recomendaciones basadas en las recetas que le gustaron al usuario
        likes = Like.objects.filter(user=usuario)
        if not likes.exists():
            return []
        recetas_gustadas = [like.receta for like in likes]
        recomendadas = Counter()
        for receta in recetas_gustadas:
            similares = self.recomendar_similares(receta, top_n=top_n)
            for sim_receta in similares:
                recomendadas[sim_receta] += 1
        # Ordenar por número de apariciones
        recetas_ordenadas = [r for r, _ in recomendadas.most_common(top_n)]
        return recetas_ordenadas


class RecomendadorSocial:
    def recomendar_por_amigos(self, usuario, top_n=10):
        # Obtener amigos (asumo modelo Amigo con user y friend)
        amigos = Amigo.objects.filter(user=usuario).values_list('friend', flat=True)
        # Recetas que les gustaron a los amigos
        likes_amigos = Like.objects.filter(user__in=amigos)
        recetas_amigos = likes_amigos.values_list('receta', flat=True)
        # Excluir recetas que ya le gustaron al usuario
        recetas_usuario = Like.objects.filter(user=usuario).values_list('receta', flat=True)
        recetas_filtradas = [r for r in recetas_amigos if r not in recetas_usuario]
        # Contar las recetas más populares entre amigos
        contador = Counter(recetas_filtradas)
        recetas_populares_ids = [receta_id for receta_id, _ in contador.most_common(top_n)]
        # Obtener objetos Receta
        recetas_populares = list(Receta.objects.filter(id__in=recetas_populares_ids))
        # Ordenar según popularidad
        recetas_populares.sort(key=lambda r: recetas_populares_ids.index(r.id))
        return recetas_populares


class ClasificadorTipoReceta:
    def __init__(self):
        self.vectorizer = None
        self.clf = None

    def entrenar(self, recetas):
        from sklearn.linear_model import LogisticRegression

        textos = [f"{r.nombre} {r.descripcion} {' '.join(r.ingredientes)}" for r in recetas]
        etiquetas = [r.tipo for r in recetas]  # Asegúrate de tener este campo

        self.vectorizer = TfidfVectorizer(stop_words='spanish')
        X = self.vectorizer.fit_transform(textos)

        self.clf = LogisticRegression(max_iter=1000)
        self.clf.fit(X, etiquetas)

    def predecir(self, receta):
        texto = f"{receta.nombre} {receta.descripcion} {' '.join(receta.ingredientes)}"
        X = self.vectorizer.transform([texto])
        return self.clf.predict(X)[0]
