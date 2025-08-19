# scripts/actualizar_calorias.py
import os
import django
import sys




sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FoodieNet.settings")
django.setup()

from recipes.models import Receta
from scripts.calorias_por_receta import calcular_macros_para_receta

def actualizar_calorias():
    recetas = Receta.objects.filter(calorias__isnull=True)
    print(f"Recetas sin calorías: {recetas.count()}")

    for receta in recetas:
        detalle = calcular_macros_para_receta(receta)
        if detalle:
            print(f"Receta {receta.id} actualizada: {detalle}")
        else:
            print(f"No se pudo actualizar la receta {receta.id}")

if __name__ == "__main__":
    actualizar_calorias()
