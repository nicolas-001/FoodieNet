from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from users.models import Amistad
from taggit.managers import TaggableManager

class Receta(models.Model):
    autor            = models.ForeignKey(User, on_delete=models.CASCADE)
    titulo           = models.CharField(max_length=255)
    descripcion      = models.TextField()
    ingredientes     = models.TextField()
    pasos            = models.TextField()
    imagen           = models.ImageField(upload_to='recipes/', blank=True, null=True)
    es_publica       = models.BooleanField(default=True)
    tiempo_preparacion = models.PositiveIntegerField(null=True, blank=True, help_text="Minutos")
    dificultad = models.CharField(
        max_length=20,
        choices=[('fácil', 'Fácil'), ('media', 'Media'), ('difícil', 'Difícil')],
        blank=True
    )
    fecha_creacion   = models.DateTimeField(auto_now_add=True)
    visitas          = models.PositiveIntegerField(default=0)   # <-- nuevo campo
    calorias = models.FloatField(null=True, blank=True)
    proteinas = models.FloatField(null=True, blank=True)
    grasas = models.FloatField(null=True, blank=True)
    carbohidratos = models.FloatField(null=True, blank=True)
    tags = TaggableManager()
    

    def __str__(self):
        return self.titulo
    def visible_para(self, user):
        if not self.es_privada:
            return True
        if self.autor == user:
            return True
        return Amistad.objects.filter(de_usuario=self.autor, para_usuario=user, aceptada=True).exists()



class Like(models.Model):
    user    = models.ForeignKey(User, on_delete=models.CASCADE)
    receta  = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name='likes')
    creado  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'receta')
        ordering = ['-creado']

    def __str__(self):
        return f"{self.user.username} le dio like a {self.receta.titulo}"

class Favorito(models.Model):
    user    = models.ForeignKey(User, on_delete=models.CASCADE)
    receta  = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name='favoritos')
    creado  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'receta')
        ordering = ['-creado']

    def __str__(self):
        return f"{self.user.username} marcó {self.receta.titulo} como favorito"
class Comentario(models.Model):
    receta  = models.ForeignKey('Receta', on_delete=models.CASCADE, related_name='comentarios')
    autor   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    texto   = models.TextField(max_length=500)
    creado  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.autor.username} en {self.receta.titulo}"