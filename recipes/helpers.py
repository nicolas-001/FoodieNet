import pandas as pd
from .models import Receta


def get_recetas_dataframe():
    recetas = Receta.objects.all().prefetch_related('tags')  # ✅ Muy importante
    data = []

    for receta in recetas:
        # DEBUG: imprime info de los tags reales
        print(f"\nReceta ID: {receta.id}")
        print(f"Objeto receta.tags: {receta.tags}")
        print(f"Tags .names(): {list(receta.tags.names())}")
        print(f"Tags .all(): {[t.name for t in receta.tags.all()]}")

        try:
            tags = list(receta.tags.names()) if receta.tags.exists() else []
        except Exception as e:
            print(f"Error al obtener tags de la receta {receta.id}: {e}")
            tags = []

        data.append({
            'id': receta.id,
            'titulo': receta.titulo,
            'tags': tags,
            'calorias': receta.calorias,
            'proteinas': receta.proteinas,
            'grasas': receta.grasas,
            'carbohidratos': receta.carbohidratos,
            # No incluimos tipo_cocina
        })

    df = pd.DataFrame(data)

    # DEBUG opcional: mostrar advertencias si hay listas de tags vacías
    for idx, row in df.iterrows():
        if not isinstance(row['tags'], list) or len(row['tags']) == 0:
            print(f"Advertencia: Receta ID {row['id']} tiene una lista de tags vacía.")

    return df

def limpiar_ingredientes(lista_ingredientes):
    ingredientes = []
    # lista_ingredientes debe ser una lista de strings (cada string puede ser multilínea)
    for item in lista_ingredientes:
        # Aseguramos que item sea string
        if not isinstance(item, str):
            continue

        lineas = item.splitlines()  # separa por líneas
        for linea in lineas:
            linea = linea.strip()
            if linea:
                ingredientes.append(linea)
    return ingredientes