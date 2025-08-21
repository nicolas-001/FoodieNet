import math

def truncar(numero, decimales=1):
    factor = 10 ** decimales
    return math.trunc(numero * factor) / factor