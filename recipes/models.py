from django.db import models
from django.conf import settings

class Receta(models.Model):
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recipes')
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField()
    ingredientes = models.TextField()
    pasos = models.TextField()
    imagen = models.ImageField(upload_to='recipes/', blank=True, null=True)
    es_publica = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo
