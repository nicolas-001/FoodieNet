from django.db import models
from django.contrib.auth.models import User
from recipes.models import Receta

class GrupoRecetas(models.Model):
    PRIVACIDAD_CHOICES = [
        ("publico", "Público"),
        ("privado", "Privado"),
    ]

    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    creador = models.ForeignKey(User, on_delete=models.CASCADE, related_name="grupos_creados")
    privacidad = models.CharField(max_length=10, choices=PRIVACIDAD_CHOICES, default="publico")
    miembros = models.ManyToManyField(User, through="GrupoMiembro", related_name="grupos")

    def puede_ver(self, usuario):
        return self.privacidad == 'publico' or usuario in self.miembros.all() or usuario == self.creador

    def puede_subir(self, usuario):
        return usuario in self.miembros.all()

    def __str__(self):
        return self.nombre


class GrupoMiembro(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    grupo = models.ForeignKey(GrupoRecetas, on_delete=models.CASCADE)
    fecha_union = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("usuario", "grupo")


class RecetaGrupo(models.Model):
    grupo = models.ForeignKey(GrupoRecetas, on_delete=models.CASCADE, related_name="recetas")
    receta = models.ForeignKey("recipes.Receta", on_delete=models.CASCADE, related_name="grupos")  # 👈 referencia correcta
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("grupo", "receta")

class PublicacionGrupo(models.Model):
    grupo = models.ForeignKey(GrupoRecetas, on_delete=models.CASCADE, related_name="publicaciones")
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="publicaciones_grupo")
    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.autor.username} en {self.grupo.nombre}"
    
class RecetaDestacadaGrupo(models.Model):
    grupo = models.ForeignKey(GrupoRecetas, on_delete=models.CASCADE, related_name="recetas_destacadas")
    receta = models.ForeignKey(Receta, on_delete=models.CASCADE)
    destacado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('grupo', 'receta')
    
class PuntosGrupo(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    grupo = models.ForeignKey(GrupoRecetas, on_delete=models.CASCADE, related_name="puntos")
    puntos = models.IntegerField(default=0)

    class Meta:
        unique_together = ("usuario", "grupo")

    def __str__(self):
        return f"{self.usuario.username} - {self.grupo.nombre}: {self.puntos} pts"