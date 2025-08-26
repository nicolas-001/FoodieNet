from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from users.models import Amistad
from taggit.managers import TaggableManager
from scripts.calorias_por_receta import calcular_macros_para_receta  # ajusta el import según tu estructura


class Receta(models.Model):
    autor            = models.ForeignKey(User, on_delete=models.CASCADE)
    titulo           = models.CharField(max_length=255)
    porciones = models.PositiveIntegerField(default=1, help_text="Número de porciones de la receta")
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
    
    def save(self, *args, **kwargs):
        try:
            # Solo calcular si hay ingredientes y no se ha calculado antes o se actualiza explícitamente
            if self.ingredientes and (self.calorias is None or kwargs.get('update_macros', False)):
                detalle = calcular_macros_para_receta(self)
                if detalle:
                    self.calorias = detalle.get("calorias_totales") or 0
                    self.proteinas = detalle.get("proteinas_totales") or 0
                    self.grasas = detalle.get("grasas_totales") or 0
                    self.carbohidratos = detalle.get("carbohidratos_totales") or 0
                else:
                    print("Advertencia: calcular_macros_para_receta devolvió None para", self.titulo)
        except Exception as e:
            print("Error calculando macros para receta '{}': {}".format(self.titulo, e))

        # Guardar la receta pase lo que pase
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo
    def visible_para(self, user):
        if not self.es_privada:
            return True
        if self.autor == user:
            return True
        return Amistad.objects.filter(de_usuario=self.autor, para_usuario=user, aceptada=True).exists()
    
    @property
    def calorias_por_persona(self):
        if self.calorias and self.porciones:
            return self.calorias / self.porciones
        return None  # O 0 si prefieres
    @property
    def proteinas_por_persona(self):
        if self.proteinas and self.porciones:
            return self.proteinas / self.porciones
        return None  # O 0 si prefieres
    @property
    def grasas_por_persona(self):
        if self.grasas and self.porciones:
            return self.grasas / self.porciones
        return None  # O 0 si prefieres
    @property
    def carbohidratos_por_persona(self):
        if self.carbohidratos and self.porciones:
            return self.carbohidratos / self.porciones
        return None  # O 0 si prefieres



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
class PlatoPersonalizado(models.Model):
    plan = models.ForeignKey("PlanDiario", on_delete=models.CASCADE, related_name="platos_personalizados")
    nombre = models.CharField(max_length=255)
    calorias = models.FloatField()
    proteinas = models.FloatField()
    grasas = models.FloatField()
    carbohidratos = models.FloatField()

    def __str__(self):
        return f"{self.nombre} ({self.calorias} kcal)"

class PlanDiario(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="planes_diarios")
    nombre = models.CharField(max_length=100, help_text="Nombre del plan, por ejemplo 'Lunes', 'Martes', etc.")
    fecha = models.DateField(auto_now_add=True)  # el día del plan
    recetas = models.ManyToManyField(Receta, related_name="planes")  # varias recetas por día

    # Totales automáticos
    calorias_totales = models.FloatField(default=0)
    proteinas_totales = models.FloatField(default=0)
    grasas_totales = models.FloatField(default=0)
    carbohidratos_totales = models.FloatField(default=0)

    def calcular_totales(self):
        """Suma los valores nutricionales de todas las recetas + platos personalizados"""
        calorias = sum(r.calorias_por_persona or 0 for r in self.recetas.all())
        proteinas = sum((r.proteinas / r.porciones) if r.proteinas else 0 for r in self.recetas.all())
        grasas = sum((r.grasas / r.porciones) if r.grasas else 0 for r in self.recetas.all())
        carbohidratos = sum((r.carbohidratos / r.porciones) if r.carbohidratos else 0 for r in self.recetas.all())

        # 🔹 añadimos los platos personalizados
        for plato in self.platos_personalizados.all():
            calorias += plato.calorias
            proteinas += plato.proteinas
            grasas += plato.grasas
            carbohidratos += plato.carbohidratos

        self.calorias_totales = calorias
        self.proteinas_totales = proteinas
        self.grasas_totales = grasas
        self.carbohidratos_totales = carbohidratos
        self.save()

    def __str__(self):
        return f"{self.nombre} - {self.usuario.username} ({self.fecha})"
    

