
from django.contrib.auth.models import User
from django.db import models

def ruta_foto_perfil(instance, filename):
    return f'perfiles/{instance.user.username}/{filename}'

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    foto = models.ImageField(upload_to=ruta_foto_perfil, default='perfiles/default.jpg', blank=True)

    def __str__(self):
        return f'Perfil de {self.user.username}'

# Create your models here.
