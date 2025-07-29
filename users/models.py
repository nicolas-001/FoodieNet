from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

def ruta_foto_perfil(instance, filename):
    return f'perfiles/{instance.user.username}/{filename}'

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    foto = models.ImageField(
        upload_to=ruta_foto_perfil,
        default='perfiles/default.jpeg',
        blank=True
    )
    biografia = models.TextField(blank=True)

    def __str__(self):
        return f'Perfil de {self.user.username}'

    @property
    def get_foto_url(self):
        if self.foto and hasattr(self.foto, 'url'):
            return self.foto.url
        return '/media/perfiles/default.jpeg'  # Ajusta según tu MEDIA_URL

    def obtener_amigos(self):
        amistades_aceptadas = Amistad.objects.filter(
            Q(de_usuario=self.user, aceptada=True) |
            Q(para_usuario=self.user, aceptada=True)
        )
        amigos = []
        for amistad in amistades_aceptadas:
            if amistad.de_usuario == self.user:
                amigos.append(amistad.para_usuario)
            else:
                amigos.append(amistad.de_usuario)
        return amigos

@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)

@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    instance.perfil.save()

class Amistad(models.Model):
    de_usuario = models.ForeignKey(User, related_name='amistades_enviadas', on_delete=models.CASCADE)
    para_usuario = models.ForeignKey(User, related_name='amistades_recibidas', on_delete=models.CASCADE)
    aceptada = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('de_usuario', 'para_usuario')

    def __str__(self):
        return f"{self.de_usuario} → {self.para_usuario} ({'Aceptada' if self.aceptada else 'Pendiente'})"
