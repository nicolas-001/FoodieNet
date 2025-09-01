from django.db import models
from django.contrib.auth.models import User
from recipes.models import Receta  # asegurarte de importar tu modelo Receta

class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('like', 'Like'),
        ('comentario', 'Comentario'),
        ('publicacion_grupo', 'Publicación en grupo'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')  # receptor
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='acciones', null=True, blank=True)  # quien hace la acción
    receta = models.ForeignKey(Receta, on_delete=models.CASCADE, null=True, blank=True)  # receta involucrada
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.usuario.username} - {self.tipo}'

