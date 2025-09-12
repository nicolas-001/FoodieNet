from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

def ruta_foto_perfil(instance, filename):
    return f'perfiles/{instance.user.username}/{filename}'


class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    foto = models.ImageField(upload_to=ruta_foto_perfil, blank=True, null=True, default="perfiles/default.jpeg")
    biografia = models.TextField(blank=True)
    edad = models.PositiveIntegerField(blank=True, null=True)
    peso = models.FloatField(blank=True, null=True)  # kg
    altura = models.FloatField(blank=True, null=True)  # cm
    sexo = models.CharField(
        max_length=10,
        choices=[("M", "Masculino"), ("F", "Femenino")],
        blank=True, null=True
    )

    # --- NUEVOS CAMPOS PARA PREFERENCIAS ---
    ingredientes_a_evitar = models.TextField(blank=True, default="", help_text="Separados por comas")
    tags_a_evitar = models.TextField(blank=True, default="", help_text="Separados por comas")
    alergias = models.TextField(blank=True, default="", help_text="Separadas por comas")

    objetivo = models.CharField(
        max_length=20,
        choices=[("deficit", "Déficit calórico"), ("mantenimiento", "Mantenimiento"), ("superavit", "Superávit calórico")],
        default="mantenimiento"
    )
    nivel_actividad = models.CharField(
        max_length=20,
        choices=[
            ("sedentario", "Sedentario"),
            ("ligero", "Ligero"),
            ("moderado", "Moderado"),
            ("activo", "Activo"),
            ("muy_activo", "Muy Activo"),
        ],
        default="sedentario"
    )

    def calcular_tmb(self):
        """Calcular TMB con fórmula Mifflin-St Jeor"""
        if not self.peso or not self.altura or not self.edad or not self.sexo:
            return None
        if self.sexo == "M":
            return 10 * self.peso + 6.25 * self.altura - 5 * self.edad + 5
        else:
            return 10 * self.peso + 6.25 * self.altura - 5 * self.edad - 161

    def calcular_calorias_objetivo(self):
        """Calcular calorías objetivo según actividad y objetivo"""
        tmb = self.calcular_tmb()
        if not tmb:
            return None

        factores = {
            "sedentario": 1.2,
            "ligero": 1.375,
            "moderado": 1.55,
            "activo": 1.725,
            "muy_activo": 1.9,
        }
        mantenimiento = tmb * factores.get(self.nivel_actividad, 1.2)

        if self.objetivo == "deficit":
            return mantenimiento - 500
        elif self.objetivo == "superavit":
            return mantenimiento + 500
        return mantenimiento

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

