from recipes.utils.traductor import traducir_ingrediente_a_ingles
import requests

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