from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import hstack
import pandas as pd
from scipy.sparse import csr_matrix

class ContentBasedRecommender:
    def __init__(self, recetas_df):
        self.df = recetas_df.copy()
        self.similarity_matrix = None

    def check_tags_format(self):
        problemas = []
        for idx, tags in enumerate(self.df['tags']):
            if not isinstance(tags, list):
                problemas.append((idx, f"tags NO es lista: {tags}"))
            elif len(tags) == 0:
                problemas.append((idx, "lista de tags VACÍA"))
            elif any(not isinstance(t, str) or t.strip() == '' for t in tags):
                problemas.append((idx, f"tags con valores no válidos: {tags}"))

        if problemas:
            print("Advertencias en tags detectadas:")
            for idx, msg in problemas:
                print(f"  - Fila {idx}: {msg}")
            return False
        return True

    def preprocess(self):
        if not self.check_tags_format():
            raise ValueError("Hay filas con tags mal formados o vacíos.")

        self.df = self.df[self.df['tags'].map(lambda x: isinstance(x, list) and len(x) > 0)]
        self.df['tags'] = self.df['tags'].apply(lambda tags: [str(t) for t in tags if t])
        self.df['tags_text'] = self.df['tags'].apply(lambda tags: ' '.join(tags))

        if 'ingredientes_text' not in self.df.columns:
            raise ValueError("Falta columna 'ingredientes_text' en DataFrame")

        self.df['ingredientes_text'] = self.df['ingredientes_text'].fillna('')
        self.df['texto_combinado'] = self.df['tags_text'] + ' ' + self.df['ingredientes_text']

        if self.df['texto_combinado'].str.strip().eq('').all():
            raise ValueError("No hay etiquetas ni ingredientes suficientes para generar recomendaciones.")

        tfidf_tags = TfidfVectorizer(sublinear_tf=True)
        tfidf_ing = TfidfVectorizer(sublinear_tf=True)

        tags_vectores = tfidf_tags.fit_transform(self.df['tags_text'])
        ingredientes_vectores = tfidf_ing.fit_transform(self.df['ingredientes_text'])

        scaler = StandardScaler()
        tiempo = self.df[['tiempo_preparacion']].fillna(0)
        tiempo_escalado = scaler.fit_transform(tiempo)

        # Aplicar pesos personalizados
        tags_vectores *= 0.6
        ingredientes_vectores *= 0.2
        tiempo_sparse = csr_matrix(tiempo_escalado) * 0.2

        self.feature_matrix = hstack([tags_vectores, ingredientes_vectores, tiempo_sparse])
        self.similarity_matrix = cosine_similarity(self.feature_matrix)


    def recomendar_similares(self, receta_id, top_n=5):
        if self.similarity_matrix is None:
            raise Exception("Debes ejecutar preprocess() primero")

        fila = self.df[self.df['id'] == receta_id]
        if fila.empty:
            raise ValueError(f"No se encontró receta con id {receta_id}")

        idx = fila.index[0]  # índice real en df

        tiempo_base = fila.iloc[0]['tiempo_preparacion']
        if pd.isna(tiempo_base):
            filtrar_tiempo = False
        else:
            filtrar_tiempo = True

        sim_scores = list(enumerate(self.similarity_matrix[idx]))

        if filtrar_tiempo:
            sim_scores = [
                (i, score) for i, score in sim_scores
                if i != idx and
                not pd.isna(self.df.iloc[i]['tiempo_preparacion']) and
                abs(self.df.iloc[i]['tiempo_preparacion'] - tiempo_base) <= 30
            ]
        else:
            sim_scores = [(i, score) for i, score in sim_scores if i != idx]

        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        top_indices = [i for i, _ in sim_scores[:top_n]]

        return self.df.iloc[top_indices][['id', 'titulo', 'tags', 'tiempo_preparacion']]
# Paso 1: Preparar tu DataFrame (ya lo tienes, por ejemplo recetas_df)

# Paso 2: Crear instancia
##recomendador = ContentBasedRecommender(recetas_df)

# Paso 3: Preprocesar (generar matrices)
#recomendador.preprocess()

# Paso 4: Obtener recomendaciones para receta con id=123
#similares = recomendador.recomendar_similares(123, top_n=5)

# Mostrar resultados
#print(similares)
