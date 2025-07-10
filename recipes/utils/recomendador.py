from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np


def recomendar_recetas(ingredientes_usuario, recetas, top_n=5):
    """
    ingredientes_usuario: lista de strings (ingredientes introducidos por usuario)
    recetas: lista de dicts con receta e ingredientes (ej: {"id": 1, "nombre": "Pizza", "ingredientes": [...]})
    """
    vocab = sorted(set(ingredientes_usuario + [ing for r in recetas for ing in r["ingredientes"]]))

    def vectorizar(ingredientes):
        return np.array([1 if ing in ingredientes else 0 for ing in vocab])

    vec_usuario = vectorizar(ingredientes_usuario)
    resultados = []
    for receta in recetas:
        vec_receta = vectorizar(receta["ingredientes"])
        sim = cosine_similarity([vec_usuario], [vec_receta])[0][0]
        resultados.append((receta, sim))

    resultados.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in resultados[:top_n]]