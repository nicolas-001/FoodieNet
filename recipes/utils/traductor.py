from googletrans import Translator

traductor = Translator()

def traducir_ingrediente_a_ingles(texto_espanol):
    try:
        traduccion = traductor.translate(texto_espanol, src='es', dest='en')
        return traduccion.text
    except Exception as e:
        print(f"[Error en traducción] {e}")
        return texto_espanol  # Si falla, envía en español para no romper el flujo
