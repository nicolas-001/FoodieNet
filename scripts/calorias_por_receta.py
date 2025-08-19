import os
from recipes.utils.nutricion import limpiar_y_dividir_ingredientes, obtener_info_nutricional_spoonacular


def calcular_macros_para_receta(receta):
    """Calcula calorías y macros para una receta y guarda los datos en la DB"""
    api_key = os.getenv('SPOONACULAR_API_KEY')
    if not api_key:
        print("API key no configurada")
        return None

    texto_ingredientes = receta.ingredientes.strip()
    if not texto_ingredientes:
        print(f"No hay ingredientes para la receta {receta.id}")
        return None

    ingredientes_lista = [linea.strip() for linea in texto_ingredientes.splitlines() if linea.strip()]
    ingredientes_lista = limpiar_y_dividir_ingredientes(ingredientes_lista)

    detalle = obtener_info_nutricional_spoonacular(ingredientes_lista, api_key)
    if detalle is None:
        print(f"Error al obtener info nutricional para la receta {receta.id}")
        return None

    # Guardar los datos en la receta
    receta.calorias = detalle["calorias_totales"]
    receta.proteinas = detalle["proteinas_totales"]
    receta.grasas = detalle["grasas_totales"]
    receta.carbohidratos = detalle["carbohidratos_totales"]
    receta.save()

    return detalle
