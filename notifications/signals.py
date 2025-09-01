from django.db.models.signals import post_save
from django.dispatch import receiver
from recipes.models import Like, Comentario, Receta
from grupos.models import PublicacionGrupo
from .models import Notificacion

# Like
@receiver(post_save, sender=Like)
def notificar_like(sender, instance, created, **kwargs):
    if created:
        receta = instance.receta
        if receta.autor != instance.user:
            Notificacion.objects.create(
                usuario=receta.autor,  # receptor
                actor=instance.user,   # quien da el like
                receta=receta,         # receta involucrada
                tipo='like',
                mensaje=f"{instance.user.username} le dio 👍 a tu receta '{receta.titulo}'."
            )

# Comentario
@receiver(post_save, sender=Comentario)
def notificar_comentario(sender, instance, created, **kwargs):
    if created:
        receta = instance.receta
        if receta.autor != instance.autor:
            Notificacion.objects.create(
                usuario=receta.autor,  # receptor
                actor=instance.autor,  # quien comenta
                receta=receta,         # receta involucrada
                tipo='comentario',
                mensaje=f"{instance.autor.username} comentó en tu receta '{receta.titulo}': {instance.texto[:50]}..."
            )

# Publicación en grupo
@receiver(post_save, sender=PublicacionGrupo)
def notificar_publicacion_grupo(sender, instance, created, **kwargs):
    if created:
        grupo = instance.grupo
        miembros = grupo.miembros.exclude(pk=instance.autor.pk)  # no notificar al autor
        for miembro in miembros:
            Notificacion.objects.create(
                usuario=miembro,       # receptor
                actor=instance.autor,  # quien publica
                tipo='publicacion_grupo',
                mensaje=f"{instance.autor.username} publicó en el grupo '{grupo.nombre}': {instance.contenido[:50]}..."
            )
