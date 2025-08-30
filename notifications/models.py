from django.db import models
from django.contrib.auth.models import User

class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('like', 'Like'),
        ('comentario', 'Comentario'),
        ('publicacion_grupo', 'Publicación en grupo'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.usuario.username} - {self.tipo}'
