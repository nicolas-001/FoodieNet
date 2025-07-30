from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import hstack

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
            raise ValueError("Hay filas con tags mal formados o vacíos. Corrige esos datos antes de continuar.")

        self.df = self.df[self.df['tags'].map(lambda x: isinstance(x, list) and len(x) > 0)]

        self.df['tags'] = self.df['tags'].apply(lambda tags: [str(t) for t in tags if t])
        self.df['tags_text'] = self.df['tags'].apply(lambda tags: ' '.join(tags))

        if 'ingredientes_text' not in self.df.columns:
            raise ValueError("Falta columna 'ingredientes_text' en DataFrame")

        self.df['texto_combinado'] = self.df['tags_text'] + ' ' + self.df['ingredientes_text']

        if self.df['texto_combinado'].str.strip().eq('').all():
            raise ValueError("No hay etiquetas ni ingredientes suficientes para generar recomendaciones.")

        tfidf = TfidfVectorizer()
        texto_vectores = tfidf.fit_transform(self.df['texto_combinado'])

        scaler = StandardScaler()
        nutricionales = scaler.fit_transform(
            self.df[['calorias', 'proteinas', 'grasas', 'carbohidratos']].fillna(0)
        )

        self.feature_matrix = hstack([texto_vectores, nutricionales])

        self.similarity_matrix = cosine_similarity(self.feature_matrix)

    def recomendar_similares(self, receta_id, top_n=5):
        if self.similarity_matrix is None:
            raise Exception("Debes ejecutar preprocess() primero")

        idx = self.df.index[self.df['id'] == receta_id].tolist()
        if not idx:
            raise ValueError(f"No se encontró receta con id {receta_id}")
        idx = idx[0]

        sim_scores = list(enumerate(self.similarity_matrix[idx]))

        # Ordenar por similitud y sacar top N excluyendo la receta misma
        sim_scores = sorted(
            [(i, score) for i, score in sim_scores if i != idx],
            key=lambda x: x[1], 
            reverse=True
        )
        top_indices = [i for i, _ in sim_scores[:top_n]]

        return self.df.iloc[top_indices][['id', 'titulo', 'tags']]
