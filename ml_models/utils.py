import pandas as pd
from recipes.models import Receta

def construir_dataframe_recetas():
    recetas = Receta.objects.all()
    data = []

    for receta in recetas:
        data.append({
            'id': receta.id,
            'titulo': receta.titulo,
            'descripcion': receta.descripcion,
            'ingredientes': receta.ingredientes,
            'pasos': receta.pasos,
            'calorias': receta.calorias,
            'proteinas': receta.proteinas,
            'grasas': receta.grasas,
            'carbohidratos': receta.carbohidratos,
            'tags': ', '.join([tag.name for tag in receta.tags.all()]),
        })

    return pd.DataFrame(data)
