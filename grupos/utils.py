from .models import PuntosGrupo

def otorgar_puntos(usuario, grupo, puntos, motivo=""):
    from .models import GrupoPuntos  # evita import circular
    GrupoPuntos.objects.create(
        usuario=usuario,
        grupo=grupo,
        puntos=puntos,
        motivo=motivo
    )
