from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Perfil

@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    perfil, creado = Perfil.objects.get_or_create(user=instance)

    # Verifica si el usuario tiene una imagen temporal cargada desde el formulario
    foto = getattr(instance, '_foto_temp', None)
    if foto:
        perfil.foto = foto
        perfil.save()

@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    try:
        instance.perfil.save()
    except Perfil.DoesNotExist:
        # En caso de que no exista el perfil, lo crea
        Perfil.objects.create(user=instance)
